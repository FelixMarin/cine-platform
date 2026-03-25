"""
Domain ports - Input ports for comments use cases
"""

# Input ports (use case interfaces)
from src.domain.ports.in.comments.add_comment_port import AddCommentPort
from src.domain.ports.in.comments.get_comments_port import GetCommentsPort
from src.domain.ports.in.comments.edit_comment_port import EditCommentPort
from src.domain.ports.in.comments.delete_comment_port import DeleteCommentPort
from src.domain.ports.in.comments.like_comment_port import LikeCommentPort
from src.domain.ports.in.comments.report_comment_port import ReportCommentPort

__all__ = [
    'AddCommentPort',
    'GetCommentsPort',
    'EditCommentPort',
    'DeleteCommentPort',
    'LikeCommentPort',
    'ReportCommentPort',
]