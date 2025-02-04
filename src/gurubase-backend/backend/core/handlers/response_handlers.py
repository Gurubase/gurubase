from rest_framework.response import Response
from rest_framework import status
from django.http import StreamingHttpResponse
from core.utils import format_date_updated, format_trust_score, format_references


class BaseResponseHandler:
    """Base class for response handlers with common functionality"""
    
    @staticmethod
    def handle_error_response(error_msg, status_code=status.HTTP_400_BAD_REQUEST):
        """Handles error responses with configurable status code"""
        return Response({'msg': str(error_msg)}, status=status_code)

    @staticmethod
    def handle_success_response(message, data=None, status_code=status.HTTP_200_OK):
        """Handles success responses with optional data"""
        response = {'msg': message}
        if data:
            response.update(data)
        return Response(response, status=status_code)


class APIResponseHandler(BaseResponseHandler):
    """Handles formatting and returning API responses"""
    
    @staticmethod
    def format_question_response(question_obj):
        """Formats a question object into a standard response format"""
        return {
            'slug': question_obj.slug,
            'content': question_obj.content,
            'question': question_obj.question,
            'date_updated': format_date_updated(question_obj.date_updated),
            'trust_score': format_trust_score(question_obj.trust_score),
            'references': format_references(question_obj.references, api=True),
            'session_id': question_obj.binge.id if question_obj.binge else None,
            'question_url': question_obj.frontend_url
        }

    @staticmethod
    def handle_stream_response(content):
        """Handles streaming responses"""
        return StreamingHttpResponse(
            content,
            content_type='text/event-stream'
        )

    @staticmethod
    def handle_non_stream_response(content):
        """Handles non-streaming responses"""
        return Response({
            'content': content,
        })


class DataSourceResponseHandler(BaseResponseHandler):
    """Handles formatting and returning data source API responses"""
    pass  # Inherits all needed methods from BaseResponseHandler 


class WidgetResponseHandler(BaseResponseHandler):
    """Handles formatting and returning widget responses"""
    
    @staticmethod
    def format_question_response(question_obj):
        """Formats a question object into a widget-specific response format"""
        return {
            'slug': question_obj.slug,
            'content': question_obj.content,
            'question': question_obj.question,
            'date_updated': format_date_updated(question_obj.date_updated),
            'trust_score': format_trust_score(question_obj.trust_score),
            'references': format_references(question_obj.references),
        }

    @staticmethod
    def handle_error_response(error_msg):
        """Handles error responses for widget endpoints"""
        return Response(
            {'error': error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )

    @staticmethod
    def handle_stream_response(content):
        """Handles streaming responses for widget endpoints"""
        return StreamingHttpResponse(
            content,
            content_type='text/event-stream'
        )

    @staticmethod
    def handle_non_stream_response(content):
        """Handles non-streaming responses for widget endpoints"""
        return Response({
            'content': content,
        }) 