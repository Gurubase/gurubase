import logging
import os
import random
import string
import requests
from django.db.models.signals import pre_delete, post_delete, post_save, pre_save
from django.conf import settings
from django.dispatch import receiver
from accounts.models import User
from core.utils import embed_text, generate_og_image, draw_text, get_default_embedding_dimensions, get_embedder_and_model, get_embedding_model_config
from core import milvus_utils
from core.models import GithubFile, GuruType, Question, RawQuestion, DataSource

from PIL import ImageColor
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from urllib.parse import urlparse
import secrets
from .models import Integration, APIKey, GuruCreationForm, OutOfContextQuestion, Settings
from .requester import MailgunRequester

logger = logging.getLogger(__name__)

# @receiver(post_save, sender=Question)
# def save_question_to_typesense(sender, instance: Question, **kwargs):
#     if settings.ENV == 'selfhosted':
#         return

#     if settings.TYPESENSE_API_KEY == "xxx":
#         return
#     curr_sitemap = instance.add_to_sitemap
#     try:
#         guru_type = instance.guru_type.slug
#     except Exception as e:
#         logger.error(f"Question {instance.id} does not have a guru_type. Writing/deleting to/from TypeSense skipped.", exc_info=True)
#         return
    
#     if not guru_type:
#         logger.error(f"Question {instance.id} does not have a guru_type. Writing/deleting to/from TypeSense skipped.")
#         return

#     from core.typesense_utils import TypeSenseClient
#     from typesense.exceptions import ObjectNotFound
#     typesense_client = TypeSenseClient(guru_type)
#     if curr_sitemap:
#         # Question is in sitemap
#         # Upsert the question to TypeSense
#         doc = {
#             'id': str(instance.id),
#             'slug': instance.slug,
#             'question': instance.question,
#             # 'content': instance.content,
#             # 'description': instance.description,
#             # 'change_count': instance.change_count,
#         }
#         try:
#             response = typesense_client.import_documents([doc])
#             logger.info(f"Upserted question {instance.id} to Typesense")
#         except Exception as e:
#             logger.error(f"Error writing question {instance.id} to Typesense: {e}", exc_info=True)

#     else:
#         # Question is not in sitemap
#         # Delete it from TypeSense
#         try:
#             response = typesense_client.delete_document(str(instance.id))
#             logger.info(f"Deleted question {instance.id} from Typesense")
#         except ObjectNotFound:
#             pass
#         except Exception as e:
#             logger.error(f"Error deleting question {instance.id} from Typesense: {e}", exc_info=True)

@receiver(post_save, sender=Question)
def generate_og_image_for_new_question(sender, instance, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    if settings.OG_IMAGE_GENERATE and instance.og_image_url=='':
        url, success = generate_og_image(instance)
        if not success:
            logger.error(f'Failure generating og images for new question with id={instance.id} : {url}')
        else:
            logger.info(f'Generated og image at {url}')

@receiver(post_delete, sender=Question)
def delete_og_image(sender, instance, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    if settings.OG_IMAGE_GENERATE and instance.og_image_url!='':
        from core.gcp import OG_IMAGES_GCP
        target_path = instance.og_image_url
        target_path = '/'.join(instance.og_image_url.split('/')[-2:])
        target_path =  f'./{settings.ENV}/{target_path}'
        logger.info(f'delete_og_image {target_path}')
        success = OG_IMAGES_GCP.delete_image(instance.id,target_path)
        if not success:
            logger.error(f'Failed to delete og_image of question with id={instance.id}')

# if you delete the question, delete it from the TypeSense index
@receiver(post_delete, sender=Question)
def delete_question_from_typesense(sender, instance: Question, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    try:
        guru_type = instance.guru_type.slug
    except Exception as e:
        logger.error(f"Question {instance.id} does not have a guru_type. Deleting from TypeSense skipped.", exc_info=True)
        return
    
    if not guru_type:
        logger.error(f"Question {instance.id} does not have a guru_type. Deleting from TypeSense skipped.", exc_info=True)
        return

    from core.typesense_utils import TypeSenseClient
    from typesense.exceptions import ObjectNotFound
    typesense_client = TypeSenseClient(guru_type)
    try:
        response = typesense_client.delete_document(str(instance.id))
    except ObjectNotFound:
        pass
    except Exception as e:
        logger.error(f"Error deleting question {instance.id} from Typesense: {e}", exc_info=True)


@receiver(post_save, sender=GuruType)
def create_base_og_image_for_guru(sender, instance: GuruType, created, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    if instance.ogimage_base_url:
        return

    if not instance.colors:
        logger.error(f'GuruType {instance.slug} has no colors')
        return

    icon_url = instance.icon_url
    if not icon_url:
        logger.error(f'GuruType {instance.slug} has no icon_url')
        return
    
    from PIL import Image, ImageDraw, ImageFont, ImageColor
    from io import BytesIO
    import requests
    from core.gcp import OG_IMAGES_GCP
    
    try:
        template_path = os.path.join(settings.STATICFILES_DIRS[0], 'backend', 'images', 'gurubase-og-image-guru-type.jpg')
        template = Image.open(template_path).convert("RGBA")

        base_color_rgb = ImageColor.getrgb(instance.colors['base_color'])
        draw_template = ImageDraw.Draw(template)

        section_x_start = 0  
        section_x_end = 456 * 2

        draw_template.rectangle(
            [section_x_start,  562 - 44 * 2, section_x_end, 562 + 44 * 2], 
            fill=(base_color_rgb[0], base_color_rgb[1], base_color_rgb[2], 255)
        )

        response = requests.get(icon_url, timeout=30)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGBA")
    
        corner_radius = 15

        # Load and resize icon
        icon_image_size = (80, 80)
        image.thumbnail(icon_image_size, Image.Resampling.LANCZOS)
        
        # Create rounded icon with white background in one step
        icon_with_bg = Image.new('RGBA', image.size, (255, 255, 255, 255))
        icon_with_bg.paste(image, (0, 0), image)
        
        # Create and apply rounded mask
        mask = Image.new('L', image.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([(0, 0), image.size], corner_radius, fill=255)
        icon_with_bg.putalpha(mask)
        
        # Create final white background with padding
        white_background = Image.new('RGBA', (100, 100), (255, 255, 255, 255))
        
        # Center icon on white background
        offset = ((100 - image.size[0]) // 2, (100 - image.size[1]) // 2)
        white_background.paste(icon_with_bg, offset, icon_with_bg)
        
        # Apply rounded corners to final background
        final_mask = Image.new('L', (100, 100), 0)
        draw_mask = ImageDraw.Draw(final_mask)
        draw_mask.rounded_rectangle([(0, 0), (100, 100)], corner_radius, fill=255)
        white_background.putalpha(final_mask)

        icon_x = 24 * 2
        icon_y = 562 - 44 * 2 + 24 * 2
        icon_position = (icon_x, icon_y)

        template.paste(white_background, icon_position, white_background)

        font_filename = 'fonts/gilroy-semibold.ttf'
        font_path = os.path.join(settings.STATICFILES_DIRS[0], 'backend', font_filename)
        
        text = instance.name + ' Guru'
        text_y = icon_y
        text_x = icon_x + white_background.width + 12 * 2
        max_width = section_x_end - text_x - 24 * 2  # Reduce by margin

        # Start with a large font size and decrease if necessary    
        initial_font_size = 88
        for font_size in range(initial_font_size, 10, -2):  # Decrement font size
            guru_font = ImageFont.truetype(font_path, font_size)
            text_y = icon_y + (white_background.size[1] - guru_font.getbbox(text)[3]) // 2
            text_width, _ = guru_font.getbbox(text)[2], guru_font.getbbox(text)[3]
            if text_width <= max_width:
                break  # Font fits within the width
        
        draw_text(draw_template, text_x, text_y, text, guru_font, max_width, 0, (255, 255, 255))

        modified_template_path = 'path_to_save_modified_template.png'
        template.save(modified_template_path)

        folder = settings.ENV
        gcpTargetPath = f'./{folder}/custom-base-templates/{instance.slug}.jpg'
        logger.debug(f'gcp target path for base og image: {gcpTargetPath}')
        
        with open(modified_template_path, 'rb') as f:
            url, success = OG_IMAGES_GCP.upload_image(f, gcpTargetPath)

        if not success:
            logger.error(f'Failed to upload og image for custom guru type {instance.slug}')
        else:
            publicly_accessible_persistent_url = url.split('?', 1)[0]
            instance.ogimage_base_url = publicly_accessible_persistent_url

        os.remove(modified_template_path)
        instance.save()
        
    except Exception as e:
        logger.error(f'Error in creating base og image for guru: {e}', exc_info=True)


@receiver(post_save, sender=GuruType)
def create_question_og_image_for_guru(sender, instance: GuruType, created, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    if instance.ogimage_url:
        return

    icon_url = instance.icon_url
    if icon_url is None or icon_url == '':
        logger.error(f'GuruType {instance.slug} has no icon_url')
        return

    if not instance.colors:
        logger.error(f'GuruType {instance.slug} has no colors')
        return

    try:
        response = requests.get(icon_url, timeout=30)
        if response.status_code != 200:
            logger.error(f'Failed to fetch icon image for custom guru type {instance.slug}')
            return
        
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        from core.gcp import OG_IMAGES_GCP

        image = Image.open(BytesIO(response.content)).convert("RGBA")

        # Load and resize icon
        icon_image_size = (140, 140)
        image.thumbnail(icon_image_size, Image.Resampling.LANCZOS)
        
        # Create rounded icon with white background in one step
        icon_with_bg = Image.new('RGBA', image.size, (255, 255, 255, 255))
        icon_with_bg.paste(image, (0, 0), image)
        
        # Create and apply rounded mask
        corner_radius = 20
        mask = Image.new('L', image.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([(0, 0), image.size], corner_radius, fill=255)
        icon_with_bg.putalpha(mask)
        
        # Create final white background with padding
        white_background = Image.new('RGBA', (160, 160), (255, 255, 255, 255))
        
        # Center icon on white background
        offset = ((160 - image.size[0]) // 2, (160 - image.size[1]) // 2)
        white_background.paste(icon_with_bg, offset, icon_with_bg)
        
        # Apply rounded corners to final background
        final_mask = Image.new('L', (160, 160), 0)
        draw_mask = ImageDraw.Draw(final_mask)
        draw_mask.rounded_rectangle([(0, 0), (160, 160)], corner_radius, fill=255)
        white_background.putalpha(final_mask)

        # Fetch the default OG image
        template_path = os.path.join(settings.STATICFILES_DIRS[0], 'backend', 'images', '0_default_og_image.jpg')
        template = Image.open(template_path)

        # Draw the far right section
        base_color_rgb = ImageColor.getrgb(instance.colors['base_color'])
        draw = ImageDraw.Draw(template)
        section_x_start = template.width - 228*2
        section_x_end = template.width
        draw.rectangle(
            [section_x_start, 0, section_x_end, 562*2],
            fill=(base_color_rgb[0], base_color_rgb[1], base_color_rgb[2], 255)
        )

        # Calculate position to paste the white background centered in the colored section
        icon_x = section_x_start + (228*2 - white_background.size[0]) // 2
        icon_y = (562*2 - ((white_background.size[1]//2)+2*2*28)) // 2

        # Paste the white background with icon
        template.paste(white_background, (icon_x, icon_y), white_background)

        font_filename = 'fonts/gilroy-semibold.ttf'
        font_path = os.path.join(settings.STATICFILES_DIRS[0], 'backend', font_filename)

        guru_font = ImageFont.truetype(font_path, 2*28) 

        # Draw the text under the icon

        # center the text to the icon
        text = instance.name
        text_y = icon_y + 160 + 2*10
        t = draw.textlength(text, font=guru_font)
        if t//2 > 80:
            text_x = icon_x - (t//2 - 80)
        else:
            text_x = icon_x + (80 - t//2)

        max_width = 228*2 - (text_x - section_x_start)
        # Start with a large font size and decrease if necessary    
        initial_font_size = 2*28
        for font_size in range(initial_font_size, 10, -2):  # Decrement font size
            guru_font = ImageFont.truetype(font_path, font_size)
            text_width, _ = guru_font.getbbox(text)[2], guru_font.getbbox(text)[3]
            if text_width <= 228*2:
                # t = draw.textlength(text, font=guru_font)
                if text_width//2 > 80:
                    text_x = icon_x - (text_width//2 - 80)
                else:
                    text_x = icon_x + (80 - text_width//2)
                break  # text fits within the width
            
            if text_width//2 > 80:
                text_x = icon_x - (text_width//2 - 80)
            else:
                text_x = icon_x + (80 - text_width//2)
            
            if text_x < section_x_start:
                continue        
        
        draw_text(draw, text_x, text_y, text, guru_font, max_width, 0, (255, 255, 255))

        text = "Guru"
        text_y = text_y + 2*28 
        
        t = draw.textlength(text, font=guru_font)
        if t//2 > 80:
            text_x = icon_x - (t//2 - 80)
        else:
            text_x = icon_x + (80 - t//2)
        draw_text(draw, text_x, text_y, text, guru_font, 228*2 - (text_x - section_x_start), 0, (255, 255, 255))

        # Save the modified template back to a file
        modified_template_path = 'path_to_save_modified_template.png'
        template.save(modified_template_path)

        folder = settings.ENV
        gcpTargetPath = f'./{folder}/custom-templates/{instance.slug}.jpg'
        logger.debug(f'gcp target path: {gcpTargetPath}')
        url, success = OG_IMAGES_GCP.upload_image(open(modified_template_path, 'rb'), gcpTargetPath)
        if not success:
            logger.error(f'Failed to upload og image for custom guru type {instance.slug}')
        else:
            publicly_accessible_persistent_url = url.split('?', 1)[0]
            instance.ogimage_url = publicly_accessible_persistent_url
        
        os.remove(modified_template_path)
        instance.save()
    except Exception as e:
        logger.error(f'Error in creating og image for guru: {e}', exc_info=True)

@receiver(post_delete, sender=Question)
def check_sitemap_upon_question_deletion(sender, instance: Question, **kwargs):
    """
    If a question is deleted, check the other questions that are not added to sitemap because of this question.
    """
    
    # If a question is not added to sitemap because of this question, check it again
    sitemap_check_questions = Question.objects.filter(add_to_sitemap=False, sitemap_reason__contains=f"Similar to question ID: ({instance.id})")
    for question in sitemap_check_questions:
        add_to_sitemap, sitemap_reason = question.is_on_sitemap()
        question.add_to_sitemap = add_to_sitemap
        question.sitemap_reason = sitemap_reason
        question.save()
    

@receiver(post_save, sender=GuruType)
def create_raw_questions_if_not_exist(sender, instance: GuruType, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    if instance.custom:
        return

    raw_questions = RawQuestion.objects.filter(guru_type=instance)
    if not raw_questions:
        raw_question = RawQuestion(guru_type=instance)
        raw_question.save()
        logger.info(f"Created raw question for {instance.slug}")


@receiver(pre_delete, sender=GuruType)
def delete_typesense_collection(sender, instance: GuruType, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    try:
        guru_type = instance.slug
    except Exception as e:
        logger.error(f"GuruType {instance.id} does not have a name. Deleting from TypeSense skipped.", exc_info=True)
        return
    
    if not guru_type:
        logger.error(f"GuruType {instance.id} does not have a name. Deleting from TypeSense skipped.", exc_info=True)
        return

    from core.typesense_utils import TypeSenseClient
    from typesense.exceptions import ObjectNotFound
    typesense_client = TypeSenseClient(guru_type)
    try:
        response = typesense_client.delete_collection()
    except ObjectNotFound:
        pass
    except Exception as e:
        logger.error(f"Error deleting collection for {guru_type} from Typesense: {e}", exc_info=True)


@receiver(post_save, sender=Question)
def save_question_to_milvus(sender, instance: Question, **kwargs):
    if instance.source not in [Question.Source.SUMMARY_QUESTION, Question.Source.RAW_QUESTION]:
        return

    if instance.binge:
        return

    if settings.ENV == 'selfhosted':
        return
    
    questions_collection_name = settings.MILVUS_QUESTIONS_COLLECTION_NAME
    if not milvus_utils.collection_exists(collection_name=questions_collection_name):
        milvus_utils.create_similarity_collection(questions_collection_name)

    # Check existence
    question_in_milvus = milvus_utils.fetch_vectors(questions_collection_name, f'id=={instance.id}', output_fields=['id', 'on_sitemap'])
    if question_in_milvus:
        # If add_to_sitemap changed, delete the old vector and reinsert
        if instance.add_to_sitemap != question_in_milvus[0]["on_sitemap"]:
            milvus_utils.delete_vectors(questions_collection_name, [str(instance.id)])
        else:
            logger.warning(f'Question {instance.id} already exists and is not changing add_to_sitemap in Milvus. Skipping...')
            return

    doc = {
        'title': instance.question,
        'slug': instance.slug,
        'id': instance.id,
        'on_sitemap': instance.add_to_sitemap,
        'guru_type': instance.guru_type.slug,
    }
    
    title_embedding = embed_text(instance.question)
    if not title_embedding:
        logger.error(f'Could not embed the title of question {instance.id}')
        return

    # description_embedding = embed_text(instance.description)
    # if not description_embedding:
    #     logger.error(f'Could not embed the description of question {instance.id}')
    #     return

    content_embedding = embed_text(instance.content)
    if not content_embedding:
        logger.error(f'Could not embed the content of question {instance.id}')
        return

    # doc['description_vector'] = description_embedding
    dimension = get_default_embedding_dimensions()
    doc['description_vector'] = [0] * dimension
    doc['title_vector'] = title_embedding
    doc['content_vector'] = content_embedding
    
    milvus_utils.insert_vectors(
        collection_name=questions_collection_name,
        docs=[doc],
        dimension=dimension
    )
    logger.info(f'Inserted question {instance.id} back into Milvus')


@receiver(pre_delete, sender=Question)
def delete_question_from_milvus(sender, instance: Question, **kwargs):
    questions_collection_name = settings.MILVUS_QUESTIONS_COLLECTION_NAME
    if not milvus_utils.collection_exists(collection_name=questions_collection_name):
        return

    if settings.ENV == 'selfhosted':
        return

    try:
        milvus_utils.delete_vectors(
            collection_name=questions_collection_name,
            ids=[str(instance.id)]
        )
    except Exception as e:
        logger.error(f"Error deleting question {instance.id} from Milvus: {e}", exc_info=True)


# @receiver(pre_save, sender=Question)
# def decide_if_english(sender, instance: Question, **kwargs): 
#     if instance.id:
#         return

#     instance.english, usages = ask_if_english(instance.question)
#     del usages['price_eval_success']
#     instance.llm_usages['english_check'] = usages

# @receiver(pre_save, sender=Question)
# def add_to_sitemap_if_possible(sender, instance: Question, **kwargs):
#     # Skip if question is already created
#     if instance.id:
#         return
#     add_to_sitemap, sitemap_reason = instance.is_on_sitemap()
#     instance.add_to_sitemap = add_to_sitemap
#     instance.sitemap_reason = sitemap_reason


@receiver(pre_delete, sender=DataSource)
def clear_data_source(sender, instance: DataSource, **kwargs):
    logger.info(f"Clearing data source: {instance.id}")
    if instance.type == DataSource.Type.PDF and instance.url:
        if settings.STORAGE_TYPE == 'gcloud':
            from core.gcp import DATA_SOURCES_GCP
            endpoint = instance.url.split('/', 4)[-1]
            DATA_SOURCES_GCP.delete_file(endpoint)
        else:
            try:
                os.remove(instance.url)
            except Exception as e:
                logger.error(f"Error deleting local file: {e}", exc_info=True)

    if instance.in_milvus:
        instance.delete_from_milvus()

    if instance.type == DataSource.Type.GITHUB_REPO:
        GithubFile.objects.filter(data_source=instance).delete()


@receiver(post_save, sender=GuruType)
def create_milvus_collection(sender, instance: GuruType, created, **kwargs):
    collection_name = instance.milvus_collection_name
    if created and not milvus_utils.collection_exists(collection_name=collection_name):
        _, dimension = get_embedding_model_config(instance.text_embedding_model)
        milvus_utils.create_context_collection(collection_name, dimension=dimension)


@receiver(pre_delete, sender=GuruType)
def delete_milvus_collection_on_guru_delete(sender, instance: GuruType, **kwargs):
    collection_name = instance.milvus_collection_name
    if milvus_utils.collection_exists(collection_name=collection_name):
        try:
            milvus_utils.drop_collection(collection_name)
            logger.info(f"Successfully deleted Milvus collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting Milvus collection {collection_name}: {e}", exc_info=True)
    else:
        logger.warning(f"Milvus collection {collection_name} does not exist, skipping deletion.")


@receiver(pre_save, sender=GuruType)
def rename_milvus_collection(sender, instance: GuruType, **kwargs):
    if instance.id:  # This is an update
        try:
            old_instance = GuruType.objects.get(id=instance.id)
            if old_instance.slug != instance.slug:
                old_collection_name = old_instance.milvus_collection_name
                new_collection_name = instance.milvus_collection_name
                if milvus_utils.collection_exists(collection_name=old_collection_name):
                    logger.info(f"Renaming Milvus collection from {old_collection_name} to {new_collection_name}")
                    milvus_utils.rename_collection(old_collection_name, new_collection_name)
                else:
                    logger.warning(f"Milvus collection {old_collection_name} does not exist, skipping rename operation")
        except GuruType.DoesNotExist:
            logger.error(f"GuruType instance with id {instance.id} not found")


@receiver(pre_save, sender=GuruType)
def rename_question_guru_types(sender, instance: GuruType, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    if instance.id:  # This is an update
        try:
            old_instance = GuruType.objects.get(id=instance.id)
            if old_instance.slug != instance.slug:
                collection_name = settings.MILVUS_QUESTIONS_COLLECTION_NAME
                # Update all questions with the old guru type to the new guru type in milvus
                questions = milvus_utils.fetch_vectors(collection_name, f'guru_type=="{old_instance.slug}"')
                
                for question in questions:
                    question['guru_type'] = instance.slug

                milvus_utils.upsert_vectors(collection_name, questions)
        except GuruType.DoesNotExist:
            logger.error(f"GuruType instance with id {instance.id} not found")


@receiver(post_save, sender=Question)
def notify_new_user_question(sender, instance: Question, created, **kwargs):
    if settings.ENV == 'selfhosted':
        return
    
    if created and settings.SLACK_NOTIFIER_ENABLED:
        payload = None
        webhook_url = None

        # Prepare the message
        question_url = instance.frontend_url
        message = f":large_green_circle: New question answered\n\n*Guru Type:* {instance.guru_type.slug}\n*Question:* {instance.question}\n*User Question:* {instance.user_question}\n*Date:* {instance.date_created}\n*URL:* {question_url}\n*Source:* {instance.source}\n*Trust Score:* {instance.trust_score:.2f}"

        if instance.user:
            message += f"\n*User Email:* {instance.user.email}"
        else:
            message += f"\n*User:* Anonymous"

        # Set the webhook url and payload if valid
        if instance.guru_type.send_notification:
            webhook_url = settings.SLACK_CUSTOM_GURU_NOTIFIER_WEBHOOK_URL
            payload = {"text": message}
        elif instance.source in [Question.Source.USER, Question.Source.WIDGET_QUESTION, Question.Source.API, Question.Source.DISCORD, Question.Source.SLACK, Question.Source.GITHUB]:
            webhook_url = settings.SLACK_NOTIFIER_WEBHOOK_URL
            payload = {"text": message}
        
        if not payload or not webhook_url:
            return

        try:
            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            logger.info(f"Slack notification sent for new question: {instance.id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification for question {instance.id}: {str(e)}", exc_info=True)

@receiver(post_save, sender=OutOfContextQuestion)
def notify_out_of_context_question(sender, instance: OutOfContextQuestion, created, **kwargs):
    if settings.ENV == 'selfhosted':
        return
    
    if created and settings.SLACK_NOTIFIER_ENABLED:
        webhook_url = None
        payload = None

        # Prepare the message
        message = f"🔴 Out of context question detected\n\n*Guru Type:* {instance.guru_type.slug}\n*User Question:* {instance.user_question}\n*Question:* {instance.question}\n*Rerank threshold:* {instance.rerank_threshold}\n*Trust score threshold:* {instance.trust_score_threshold}\n*Source:* {instance.source}\n*Date:* {instance.date_created}\n*Enhanced question:* {instance.enhanced_question}"


        if instance.guru_type.send_notification:
            webhook_url = settings.SLACK_CUSTOM_GURU_NOTIFIER_WEBHOOK_URL
            payload = {"text": message}
        elif instance.source in [Question.Source.USER, Question.Source.WIDGET_QUESTION, Question.Source.API, Question.Source.DISCORD, Question.Source.SLACK]:
            webhook_url = settings.SLACK_NOTIFIER_WEBHOOK_URL
            payload = {"text": message}

        try:
            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification for out of context question: {str(e)}", exc_info=True)


@receiver(post_save, sender=User)
def notify_new_user(sender, instance: User, created, **kwargs):
    if settings.ENV == 'selfhosted':
        return

    if created and settings.SLACK_NOTIFIER_ENABLED:
        message = f"⚡️ New user signed up: {instance.email} ({instance.name}) via {instance.auth_provider}"
        
        webhook_url = settings.SLACK_NOTIFIER_WEBHOOK_URL
        payload = {"text": message}
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            logger.info(f"Slack notification sent for new user: {instance.email}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification for user {instance.email}: {str(e)}", exc_info=True)


@receiver(pre_save, sender=DataSource)
def update_data_source_in_milvus(sender, instance: DataSource, **kwargs):
    # TODO: Test this
    # If 
    # - The data source is being updated
    # - The title of the data source is changed
    # - The data source is written to milvus and has document ids
    # Then we need to update the vector in milvus

    # Return it newly created
    if not instance.id:
        return

    if instance.type == DataSource.Type.GITHUB_REPO:
        return

    # Cases:
    # 1- New creation
    # 2- Not written to milvus
    #   2-a. Title changed
    #   2-b. Title not changed
    # 3- Written to milvus
    #   3-a. Title changed
    #   3-b. Title not changed

    # Each doc is of format
    # {
    #     "metadata": {
    #         "type": type,
    #         "link": link,
    #         "split_num": split_num,
    #         "title": title,
    #     },
    #     "text": split,
    #     "vector": embeddings[i],
    # }
    
    # Get the old title
    old_instance = DataSource.objects.get(id=instance.id)

    title_changed = old_instance.title != instance.title
    if title_changed and instance.in_milvus and instance.doc_ids:
        collection_name = instance.guru_type.milvus_collection_name
        if milvus_utils.collection_exists(collection_name=collection_name):
            docs = milvus_utils.fetch_vectors(collection_name, f'metadata["link"] == "{instance.url}"')
            for doc in docs:
                doc['metadata']['title'] = instance.title
                
            # Remove the old vectors
            milvus_utils.delete_vectors(collection_name, [str(doc['id']) for doc in docs])

            for doc in docs:
                del doc['id']

            # Insert the new vectors
            dimension = get_embedding_model_config(instance.guru_type.code_embedding_model)[1]
            ids = milvus_utils.insert_vectors(collection_name, docs, dimension=dimension)
            instance.doc_ids = list(ids)

@receiver(pre_delete, sender=GuruType)
def delete_guru_type_questions(sender, instance: GuruType, **kwargs):
    """Delete all questions associated with a guru type when it's deleted"""
    try:
        Question.objects.filter(guru_type=instance).delete()
        logger.info(f"Deleted all questions for guru type: {instance.slug}")
    except Exception as e:
        logger.error(f"Error deleting questions for guru type {instance.slug}: {e}", exc_info=True)


@receiver(pre_delete, sender=GithubFile)
def clear_github_file(sender, instance: GithubFile, **kwargs):
    if instance.in_milvus:
        logger.info(f"Clearing github file: {instance.id}")
        instance.delete_from_milvus()

@receiver(pre_save, sender=GuruType)
def validate_github_repos(sender, instance, **kwargs):
    """Validate GitHub repo URLs format if provided"""
    if instance.github_repos:
        # Ensure github_repos is a list
        if not isinstance(instance.github_repos, list):
            raise ValidationError({'msg': 'github_repos must be a list'})
            
        for repo_url in instance.github_repos:
            # Normalize URL by removing trailing slash
            repo_url = repo_url.rstrip('/')
            
            # Validate URL format
            url_validator = URLValidator()
            try:
                url_validator(repo_url)
            except ValidationError:
                raise ValidationError({'msg': f'Invalid URL format: {repo_url}'})

            # Ensure it's a GitHub URL
            parsed_url = urlparse(repo_url)
            if not parsed_url.netloc.lower() in ['github.com', 'www.github.com']:
                raise ValidationError({'msg': f'URL must be a GitHub repository: {repo_url}'})
                
            # Ensure it has a path (repository)
            if not parsed_url.path or parsed_url.path == '/':
                raise ValidationError({'msg': f'Invalid GitHub repository URL: {repo_url}'})

            # Ensure URL has valid scheme
            if parsed_url.scheme not in ['http', 'https']:
                raise ValidationError({'msg': f'URL must start with http:// or https://: {repo_url}'})

@receiver(post_save, sender=GuruType)
def manage_github_repo_datasource(sender, instance, **kwargs):
    from core.tasks import data_source_retrieval
    """Manage DataSource based on github_repos and index_repo fields"""
    
    # Get all existing GitHub repo data sources for this guru type
    existing_datasources = DataSource.objects.filter(
        guru_type=instance,
        type=DataSource.Type.GITHUB_REPO,
    )
    
    # Create a map of existing data sources by URL
    existing_datasources_map = {ds.url: ds for ds in existing_datasources}
    
    # Case 1: URLs exist and index_repo is True - Create/Update DataSources
    if instance.github_repos and instance.index_repo:
        current_urls = set(instance.github_repos)
        existing_urls = set(existing_datasources_map.keys())
        
        # URLs to add
        urls_to_add = current_urls - existing_urls
        for url in urls_to_add:
            DataSource.objects.create(
                guru_type=instance,
                type=DataSource.Type.GITHUB_REPO,
                url=url,
                status=DataSource.Status.NOT_PROCESSED
            )
        
        # URLs to remove
        urls_to_remove = existing_urls - current_urls
        for url in urls_to_remove:
            existing_datasources_map[url].delete()
            
        if urls_to_add or urls_to_remove:
            data_source_retrieval.delay(guru_type_slug=instance.slug, countdown=1)

    # Case 2: Either URLs list is empty or index_repo is False - Delete all DataSources
    elif existing_datasources.exists():
        existing_datasources.delete()

@receiver(post_save, sender=DataSource)
def data_source_retrieval_on_creation(sender, instance: DataSource, created, **kwargs):
    from core.tasks import data_source_retrieval

    if created and instance.status == DataSource.Status.NOT_PROCESSED:
        data_source_retrieval.delay(guru_type_slug=instance.guru_type.slug, countdown=1)

@receiver(pre_save, sender=Integration)
def create_api_key_for_integration(sender, instance, **kwargs):
    if not instance.api_key_id:
        if instance.guru_type.maintainers.first():
            user = instance.guru_type.maintainers.first()
        else:
            user = User.objects.filter(email=settings.ROOT_EMAIL).first()

        api_key = APIKey.objects.create(
            user=user,
            key="gb-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=30)),
            integration=True
        )
        instance.api_key = api_key

@receiver(pre_save, sender=Integration)
def manage_slack_channels(sender, instance, **kwargs):
    """Manage Slack channel membership when channels are updated."""
    if instance.type != Integration.Type.SLACK:
        return
        
    try:
        # Get the old instance if it exists
        if instance.id:
            old_instance = Integration.objects.get(id=instance.id)
            old_channels = {
                channel['id']: channel.get('allowed', False) 
                for channel in old_instance.channels
            }
        else:
            old_channels = {}
            
        new_channels = {
            channel['id']: channel.get('allowed', False) 
            for channel in instance.channels
        }
        
        # Skip if no changes to channels
        if old_channels == new_channels:
            return
            
        from slack_sdk import WebClient
        client = WebClient(token=instance.access_token)
        
        # Leave channels that are no longer allowed
        channels_to_leave = [
            channel_id for channel_id, was_allowed in old_channels.items()
            if was_allowed and (
                channel_id not in new_channels or  # Channel removed
                not new_channels[channel_id]       # Channel no longer allowed
            )
        ]
        
        # Join newly allowed channels
        channels_to_join = [
            channel_id for channel_id, is_allowed in new_channels.items()
            if is_allowed and (
                channel_id not in old_channels or  # New channel
                not old_channels[channel_id]       # Previously not allowed
            )
        ]
        
        # Leave channels
        # for channel_id in channels_to_leave:
        #     try:
        #         client.conversations_leave(channel=channel_id)
        #     except Exception as e:
        #         logger.warning(f"Failed to leave Slack channel {channel_id}: {e}", exc_info=True)
                
        # Join channels
        for channel_id in channels_to_join:
            try:
                client.conversations_join(channel=channel_id)
            except Exception as e:
                logger.warning(f"Failed to join Slack channel {channel_id}: {e}", exc_info=True)
                
    except Integration.DoesNotExist:
        pass  # This is a new integration
    except Exception as e:
        logger.warning(f"Failed to manage Slack channels for integration {instance.id}: {e}", exc_info=True)

@receiver(pre_delete, sender=Integration)
def handle_integration_deletion(sender, instance, **kwargs):
    """
    Wrapper signal to handle all cleanup operations when an integration is deleted.
    Order of operations:
    1. Platform-specific cleanup (Discord: leave guild, Slack: leave channels)
    2. Revoke access token
    3. Delete API key
    """
    # Step 1: Platform-specific cleanup
    if settings.ENV != 'selfhosted':
        if instance.type == Integration.Type.DISCORD:
            try:
                from core.integrations.factory import IntegrationFactory
                discord_strategy = IntegrationFactory.get_strategy('DISCORD', instance)
                
                def leave_guild():
                    headers = {
                        'Authorization': f'Bot {discord_strategy._get_bot_token(instance)}'
                    }
                    guild_id = instance.external_id
                    url = f'https://discord.com/api/v10/users/@me/guilds/{guild_id}'
                    
                    response = requests.delete(url, headers=headers)
                    if response.status not in [200, 204]:
                        response_data = response.json()
                        logger.warning(f"Failed to leave Discord guild {guild_id}: {response_data}")
                
                leave_guild()
            except Exception as e:
                logger.warning(f"Failed to leave Discord guild for integration {instance.id}: {e}", exc_info=True)

        # Step 2: Revoke access token
        try:
            from core.integrations.factory import IntegrationFactory
            strategy = IntegrationFactory.get_strategy(instance.type, instance)
            strategy.revoke_access_token()
        except Exception as e:
            logger.warning(f"Failed to revoke access token for integration {instance.id}: {e}", exc_info=True)
            # Continue with deletion even if token revocation fails

        if instance.api_key:
            instance.api_key.delete()

    if instance.type == Integration.Type.GITHUB:
        from .github.app_handler import GithubAppHandler
        GithubAppHandler(instance).clear_redis_cache()

@receiver(post_save, sender=GuruCreationForm)
def notify_admin_on_guru_creation_form_submission(sender, instance, **kwargs):
    if instance.notified:
        return

    # Send email notification
    subject = f'New Guru Creation Request - {instance.docs_url[:150]}'
    message = f"""
A new guru creation request has been submitted:

Name: {instance.name}
Email: {instance.email}
Documentation URL: {instance.docs_url}
GitHub Repository: {instance.github_repo}
Use Case: {instance.use_case}
Source: {instance.source}

View this request in the admin panel.
"""
        
    MailgunRequester().send_email(settings.ADMIN_EMAIL, subject, message)
    instance.notified = True
    instance.save()

@receiver(pre_save, sender=GuruType)
def handle_embedding_model_change(sender, instance, **kwargs):
    """
    Signal handler that delegates text embedding model reindexing to a celery task when text_embedding_model changes.
    """
    if settings.ENV == 'selfhosted':
        return
        if instance.text_embedding_model in [GuruType.EmbeddingModel.GEMINI_EMBEDDING_001, GuruType.EmbeddingModel.GEMINI_TEXT_EMBEDDING_004]:
            raise ValidationError({'msg': 'Cannot change text_embedding_model to Gemini models in selfhosted environment'})

        if instance.code_embedding_model in [GuruType.EmbeddingModel.GEMINI_EMBEDDING_001, GuruType.EmbeddingModel.GEMINI_TEXT_EMBEDDING_004]:
            raise ValidationError({'msg': 'Cannot change code_embedding_model to Gemini models in selfhosted environment'})

    if instance.id:  # Only for existing guru types
        try:
            old_instance = GuruType.objects.get(id=instance.id)
            if old_instance.text_embedding_model != instance.text_embedding_model:
                # Check if the guru has not processed data sources, reject if so
                if DataSource.objects.filter(guru_type=instance, status=DataSource.Status.NOT_PROCESSED).exists():
                    raise ValidationError({'msg': 'Cannot change text_embedding_model until data sources have been completely processed (either success or fail)'})

                # Store the model choices for the task
                old_model = old_instance.text_embedding_model
                new_model = instance.text_embedding_model

                # Schedule the reindexing task
                from core.tasks import reindex_text_embedding_model
                reindex_text_embedding_model.delay(instance.id, old_model, new_model)

            if old_instance.code_embedding_model != instance.code_embedding_model:
                if DataSource.objects.filter(guru_type=instance, status=DataSource.Status.NOT_PROCESSED).exists():
                    raise ValidationError({'msg': 'Cannot change code_embedding_model until data sources have been completely processed (either success or fail)'})

                # Store the model choices for the task
                old_model = old_instance.code_embedding_model
                new_model = instance.code_embedding_model

                # Schedule the reindexing task
                from core.tasks import reindex_code_embedding_model
                reindex_code_embedding_model.delay(instance.id, old_model, new_model)
                    
        except GuruType.DoesNotExist:
            pass  # This is a new guru type

@receiver(pre_save, sender=Settings)
def handle_selfhosted_embedding_model_change(sender, instance, **kwargs):
    """
    Signal handler that delegates embedding model reindexing to a celery task when ai provider or embedding model changes on selfhosted. 
    """
    if settings.ENV != 'selfhosted':
        return

    # ai_provider_changed = False
    # ollama_embedding_model_changed = False

    if not instance.id:
        return

    if instance.ai_model_provider == Settings.AIProvider.OPENAI:
        if not instance.is_openai_key_valid:
            return
    else:
        if not instance.is_ollama_url_valid:
            return
        
        if not instance.is_ollama_embedding_model_valid:
            return

    old_instance = Settings.objects.get(id=instance.id)
    old_model = old_instance.last_valid_embedding_model
    old_model_dimension = old_instance.last_valid_embedding_model_dimension

    if old_model == Settings.DefaultEmbeddingModel.SELFHOSTED.value:
        _, old_model = get_embedder_and_model(old_model, sync=False)

    new_model = instance.last_valid_embedding_model
    new_model_dimension = instance.last_valid_embedding_model_dimension
    if new_model == Settings.DefaultEmbeddingModel.SELFHOSTED.value:
        _, new_model = get_embedder_and_model(new_model, sync=False)

    if old_model == new_model:
        return

    guru_types = GuruType.objects.all()
    from core.tasks import reindex_code_embedding_model, reindex_text_embedding_model
    for guru_type in guru_types:
        reindex_code_embedding_model.delay(guru_type.id, old_model, new_model)
        reindex_text_embedding_model.delay(guru_type.id, old_model, new_model, old_model_dimension, new_model_dimension)