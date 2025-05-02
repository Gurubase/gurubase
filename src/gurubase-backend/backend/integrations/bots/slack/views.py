from asgiref.sync import sync_to_async
from rest_framework.test import APIRequestFactory
from slack_sdk.errors import SlackApiError
import logging
import aiohttp
import time
from django.conf import settings
from django.core.cache import caches
from slack_sdk import WebClient

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from core.utils import get_base_url
from core.views import api_answer
from integrations.bots.helpers import NotEnoughData, NotRelated, cleanup_title, get_trust_score_emoji, strip_first_header
from integrations.bots.views import get_or_create_thread_binge
from integrations.models import Integration
from integrations.factory import IntegrationFactory
from rest_framework.decorators import api_view
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
def slack_events(request):
    """Handle Slack events including verification and message processing."""
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    import asyncio
    import threading
    from django.core.cache import caches
    
    data = request.data
    
    # If this is a verification request, respond with the challenge parameter
    if "challenge" in data:
        return Response(data["challenge"], status=status.HTTP_200_OK)
    
    # Handle the event in a separate thread
    if "event" in data:
        def process_event():
            try:
                event = data["event"]
                
                # Only proceed if it's a message event and not from a bot
                if event["type"] == "message" and "subtype" not in event and event.get("user") != event.get("bot_id"):
                    dm = False
                    if event['channel_type'] == 'im':
                        dm = True
                    # Get bot user ID from authorizations
                    bot_user_id = data.get("authorizations", [{}])[0].get("user_id")
                    user_message = event["text"]
                    
                    # # First check if the bot is mentioned
                    # if not (bot_user_id and f"<@{bot_user_id}>" in user_message):
                    #     return
                    if dm and event['user'] == bot_user_id:
                        return
                        
                    team_id = data.get('team_id')
                    if not team_id:
                        return
                        
                    # Try to get integration from cache first
                    cache = caches['alternate']
                    cache_key = f"slack_integration:{team_id}"
                    integration = cache.get(cache_key)
                    
                    if not integration:
                        try:
                            # If not in cache, get from database
                            integration = Integration.objects.get(type=Integration.Type.SLACK, external_id=team_id)
                            # Set cache timeout to 0. This is because dynamic channel updates are not immediately reflected
                            # And this may result in bad UX, and false positive bug reports
                            cache.set(cache_key, integration, timeout=0)
                        except Integration.DoesNotExist:
                            logger.error(f"No integration found for team {team_id}", exc_info=True)
                            return
                    
                    try:
                        # Get the Slack client for this team
                        client = WebClient(token=integration.access_token)
                        
                        channel_id = event["channel"]
                        
                        # Check if the current channel is allowed
                        channel_allowed = False
                        if not dm:
                            channels = integration.channels
                            channel_allowed = False
                            for channel in channels:
                                if str(channel.get('id')) == channel_id and channel.get('allowed', False):
                                    channel_allowed = True
                                    break
                        else:
                            channel_allowed = integration.allow_dm

                        if not dm and channel_mode == 'manual' and not (bot_user_id and f"<@{bot_user_id}>" in user_message):
                            # Check manual mode and bot mention only for non-DMs
                            return

                        # Get thread_ts if it exists (means we're in a thread)
                        thread_ts = event.get("thread_ts") or event.get("ts")

                        # thread_ts means we're in a thread
                        if event.get('thread_ts') and not (bot_user_id and f"<@{bot_user_id}>" in user_message):
                            return
                        
                        if not channel_allowed:
                            # Run the unauthorized message handler in the event loop
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(send_channel_unauthorized_message(
                                    client=client,
                                    channel_id=channel_id,
                                    thread_ts=thread_ts,
                                    guru_slug=integration.guru_type.slug,
                                    dm=dm
                                ))
                            finally:
                                loop.close()
                            return
                        
                        # Remove the bot mention from the message
                        clean_message = user_message.replace(f"<@{bot_user_id}>", "").strip()
                        
                        # Run the async handler in a new event loop
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(handle_slack_message(
                                client=client,
                                integration=integration,
                                channel_id=channel_id,
                                thread_ts=thread_ts,
                                clean_message=clean_message
                            ))
                        except SlackApiError as e:
                            if e.response.data.get('msg') in ['token_expired', 'invalid_auth', 'not_authed']:
                                try:
                                    # Get fresh integration data from DB
                                    integration = Integration.objects.get(id=integration.id)
                                    # Try to refresh the token
                                    strategy = IntegrationFactory.get_strategy(integration.type, integration)
                                    new_token = strategy.handle_token_refresh()
                                    
                                    # Update cache with new integration data
                                    cache.set(cache_key, integration, timeout=300)
                                    
                                    # Retry with new token
                                    client = WebClient(token=new_token)
                                    loop.run_until_complete(handle_slack_message(
                                        client=client,
                                        integration=integration,
                                        channel_id=channel_id,
                                        thread_ts=thread_ts,
                                        clean_message=clean_message
                                    ))
                                except Exception as refresh_error:
                                    logger.error(f"Error refreshing token: {refresh_error}", exc_info=True)
                            else:
                                logger.error(f"Slack API error: {e}", exc_info=True)
                        finally:
                            loop.close()
                            
                    except Exception as e:
                        logger.error(f"Error processing Slack event: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error in process_event thread: {e}", exc_info=True)
        
        # Start processing in a separate thread
        thread = threading.Thread(target=process_event)
        thread.daemon = True  # Make thread daemon so it doesn't block server shutdown
        thread.start()
    
    # Return 200 immediately
    return Response(status=200)


def convert_markdown_to_slack(content: str) -> str:
    """Convert Markdown formatting to Slack formatting."""
    # Convert markdown code blocks to Slack code blocks by removing language specifiers
    import re
    
    # First remove language specifiers from code blocks
    content = re.sub(r'```\w+', '```', content)
    
    # Then remove empty lines at the start and end of code blocks
    def trim_code_block(match):
        code_block = match.group(0)
        lines = code_block.split('\n')
        
        # Find first and last non-empty lines (excluding ```)
        start = 0
        end = len(lines) - 1
        
        # Find first non-empty line after opening ```
        for i, line in enumerate(lines):
            if line.strip() == '```':
                start = i + 1
                break
                
        # Find last non-empty line before closing ```
        for i in range(len(lines) - 1, -1, -1):
            if line.strip() == '```':
                end = i
                break
                
        # Keep all lines between start and end (inclusive)
        return '```\n' + '\n'.join(lines[start:end]) + '\n```'
    
    content = re.sub(r'```[\s\S]+?```', trim_code_block, content)
    
    # Convert markdown links [text](url) to Slack format <url|text>
    def replace_link(match):
        text = match.group(1)
        url = match.group(2)
        return f"<{url}|{text}>"
    
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)
    
    # Convert markdown bold/italic to Slack format
    # First handle single asterisks for italics (but not if they're part of double asterisks)
    i = 0
    while i < len(content):
        if content[i:i+2] == "**":
            i += 2
        elif content[i] == "*":
            # Replace single asterisk with underscore for italics
            content = content[:i] + "_" + content[i+1:]
        i += 1
    
    # Then handle double asterisks for bold
    content = content.replace("**", "*")
    
    return content

def format_slack_response(content: str, trust_score: int, references: list, question_url: str) -> str:
    """Format the response with trust score and references for Slack.
    Using Slack's formatting syntax:
    *bold*
    _italic_
    ~strikethrough~
    `code`
    ```preformatted```
    >blockquote
    <url|text> for links
    """
    # Strip header from content
    content = strip_first_header(content)
    
    # Convert markdown to slack formatting
    content = convert_markdown_to_slack(content)
    
    formatted_msg = [content]
    
    # Add trust score with emoji
    trust_emoji = get_trust_score_emoji(trust_score)
    formatted_msg.append(f"\n---------\n_*Trust Score*: {trust_emoji} {trust_score}_%")
    
    # Add references if they exist
    if references:
        formatted_msg.append("\n_*Sources*_:")
        for ref in references:
            # First remove Slack-style emoji codes with adjacent spaces
            clean_title = cleanup_title(ref['title'])
            
            formatted_msg.append(f"\n• _<{ref['link']}|{clean_title}>_")
    
    # Add frontend link if it exists
    if question_url:
        formatted_msg.append(f"\n:eyes: _<{question_url}|View on Gurubase for a better UX>_")
    
    return "\n".join(formatted_msg)

async def stream_and_update_message(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    payload: dict,
    client: WebClient,
    channel_id: str,
    message_ts: str,
    thread_ts: str,
    update_interval: float = 0.5
) -> None:
    """Stream the response and update the Slack message periodically."""
    last_update = time.time()
    current_content = ""
    
    try:
        # Create request using APIRequestFactory
        factory = APIRequestFactory()
        guru_type = payload.get('guru_type')

        payload['channel_id'] = channel_id
        if thread_ts:
            payload['thread_ts'] = thread_ts
        
        request = factory.post(
            f'/api/v1/{guru_type}/answer/',
            payload,
            HTTP_X_API_KEY=headers.get('X-API-KEY'),
            format='json'
        )
        
        # Call api_answer directly in a sync context
        response = await sync_to_async(api_answer)(request, guru_type)
        
        # Handle StreamingHttpResponse
        if hasattr(response, 'streaming_content'):
            buffer = ""
            line_buffer = ""
            
            # Create an async wrapper for the generator iteration
            @sync_to_async
            def get_next_chunk():
                try:
                    return next(response.streaming_content)
                except StopIteration:
                    return None
            
            # Iterate over the generator asynchronously
            while True:
                chunk = await get_next_chunk()
                if chunk is None:
                    # Yield any remaining text in the buffer
                    if line_buffer.strip():
                        buffer += line_buffer
                        # Strip header and convert markdown
                        cleaned_content = strip_first_header(buffer)
                        if cleaned_content.strip():
                            formatted_content = convert_markdown_to_slack(cleaned_content)
                            formatted_content += '\n\n:clock1: _streaming..._'
                            try:
                                client.chat_update(
                                    channel=channel_id,
                                    ts=message_ts,
                                    text=formatted_content
                                )
                            except SlackApiError as e:
                                logger.error(f"Error updating message: {e.response}", exc_info=True)
                    break
                    
                if chunk:
                    text = chunk.decode('utf-8') if isinstance(chunk, bytes) else str(chunk)
                    line_buffer += text
                    
                    # Check if we have complete lines
                    while '\n' in line_buffer:
                        line, line_buffer = line_buffer.split('\n', 1)
                        if line.strip():
                            buffer += line + '\n'
                            # Strip header and convert markdown
                            cleaned_content = strip_first_header(buffer)
                            if cleaned_content.strip():
                                formatted_content = convert_markdown_to_slack(cleaned_content)
                                formatted_content += '\n\n:clock1: _streaming..._'
                                current_time = time.time()
                                if current_time - last_update >= update_interval:
                                    try:
                                        client.chat_update(
                                            channel=channel_id,
                                            ts=message_ts,
                                            text=formatted_content
                                        )
                                        last_update = current_time
                                    except SlackApiError as e:
                                        logger.error(f"Error updating message: {e.response}", exc_info=True)
                                        client.chat_update(
                                            channel=channel_id,
                                            ts=message_ts,
                                            text="❌ Failed to update message"
                                        )
                                        return
    except Exception as e:
        logger.error(f"Error in stream_and_update_message: {str(e)}", exc_info=True)
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="❌ An error occurred while processing your request"
        )
        return

async def get_final_response(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    payload: dict,
    client: WebClient,
    channel_id: str,
    message_ts: str
) -> None:
    """Get and send the final formatted response."""
    try:
        # Create request using APIRequestFactory
        factory = APIRequestFactory()
        guru_type = payload.get('guru_type')
        
        request = factory.post(
            f'/api/v1/{guru_type}/answer/',
            payload,
            HTTP_X_API_KEY=headers.get('X-API-KEY'),
            format='json'
        )
        
        # Call api_answer directly
        response = await sync_to_async(api_answer)(request, guru_type)
        
        # Convert response to dict if it's a Response object
        if hasattr(response, 'data'):
            final_response = response.data
        else:
            final_response = response

        if 'msg' in final_response and 'doesn\'t have enough data' in final_response['msg']:
            raise NotEnoughData(final_response['msg'])
        elif 'msg' in final_response and 'is not related to' in final_response['msg']:
            raise NotRelated(final_response['msg'])
        elif 'msg' in final_response:
            raise Exception(final_response['msg'])

        trust_score = final_response.get('trust_score', 0)
        references = final_response.get('references', [])
        content = final_response.get('content', '')
        question_url = final_response.get('question_url', '')

        final_text = format_slack_response(content, trust_score, references, question_url)
        if final_text.strip():  # Only update if there's content after stripping header
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=final_text
            )
    except NotEnoughData as e:
        logger.error(f"Not enough data: {str(e)}", exc_info=True)
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"❌ {str(e)}"
        )
    except NotRelated as e:
        logger.error(f"Not related to the question: {str(e)}", exc_info=True)
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"❌ {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error in get_final_response: {str(e)}", exc_info=True)
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="❌ An error occurred while processing your request"
        )

async def handle_slack_message(
    client: WebClient,
    integration: Integration,
    channel_id: str,
    thread_ts: str,
    clean_message: str
) -> None:
    """Handle a single Slack message."""
    if not clean_message:
        thinking_response = client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="Please provide a valid question. 🤔"
        )
        return

    try:
        # First send a thinking message
        thinking_response = client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="Thinking... 🤔"
        )
        
        try:
            # Get or create thread and binge
            _, binge = await sync_to_async(get_or_create_thread_binge)(thread_ts, integration)
        except Exception as e:
            logger.error(f"Error creating thread/binge: {str(e)}", exc_info=True)
            client.chat_update(
                channel=channel_id,
                ts=thinking_response["ts"],
                text="❌ Failed to create conversation thread"
            )
            return
        
        guru_type_slug = await sync_to_async(lambda integration: integration.guru_type.slug)(integration)
        api_key = await sync_to_async(lambda integration: integration.api_key.key)(integration)
        
        try:
            # First get streaming response
            stream_payload = {
                'question': clean_message,
                'stream': True,
                'short_answer': True,
                'session_id': str(binge.id),
                'guru_type': guru_type_slug
            }
            
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                await stream_and_update_message(
                    session=session,
                    url='',  # Not used anymore
                    headers=headers,
                    payload=stream_payload,
                    client=client,
                    channel_id=channel_id,
                    message_ts=thinking_response["ts"],
                    thread_ts=thread_ts
                )
                
                # Then get final formatted response
                final_payload = {
                    'question': clean_message,
                    'stream': False,
                    'short_answer': True,
                    'fetch_existing': True,
                    'session_id': str(binge.id),
                    'guru_type': guru_type_slug
                }
                
                await get_final_response(
                    session=session,
                    url='',  # Not used anymore
                    headers=headers,
                    payload=final_payload,
                    client=client,
                    channel_id=channel_id,
                    message_ts=thinking_response["ts"]
                )
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {str(e)}", exc_info=True)
            client.chat_update(
                channel=channel_id,
                ts=thinking_response["ts"],
                text="❌ Network error occurred while processing your request"
            )
        except Exception as e:
            logger.error(f"Error in API communication: {str(e)}", exc_info=True)
            client.chat_update(
                channel=channel_id,
                ts=thinking_response["ts"],
                text="❌ An error occurred while processing your request"
            )
    except SlackApiError as e:
        logger.error(f"Slack API error: {str(e)}", exc_info=True)
        # If we can't even send the thinking message, we can't update it later
        try:
            if thinking_response:
                client.chat_update(
                    channel=channel_id,
                    ts=thinking_response["ts"],
                    text="❌ Failed to process your request due to a Slack API error"
                )
            else:
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text="❌ Failed to process your request due to a Slack API error"
                )
        except:
            pass  # If this fails too, we can't do much
    except Exception as e:
        logger.error(f"Unexpected error in handle_slack_message: {str(e)}", exc_info=True)
        try:
            if thinking_response:
                client.chat_update(
                    channel=channel_id,
                    ts=thinking_response["ts"],
                    text="❌ An unexpected error occurred"
                )
            else:
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text="❌ An unexpected error occurred"
                )
        except:
            pass  # If this fails too, we can't do much

async def send_channel_unauthorized_message(
    client: WebClient,
    channel_id: str,
    thread_ts: str,
    guru_slug: str,
    dm: bool
) -> None:
    """Send a message explaining how to authorize the channel."""
    try:
        base_url = await sync_to_async(get_base_url)()
        settings_url = f"{base_url.rstrip('/')}/guru/{guru_slug}/integrations/slack"
        if dm:
            message = (
                "❌ Bot direct messages are not enabled.\n\n"
                f"Please visit <{settings_url}|Gurubase Settings> to configure "
                "the bot and enable direct messages."
            )
        else:
            message = (
                "❌ This channel is not authorized to use the bot.\n\n"
                f"Please visit <{settings_url}|Gurubase Settings> to configure "
                "the bot and add this channel to the allowed channels list."
            )
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=message
        )
    except SlackApiError as e:
        logger.error(f"Error sending unauthorized channel message: {e.response}", exc_info=True)
