"""
Servicios auxiliares para comentarios
"""

from typing import Optional, List, Dict, Any
import re
from datetime import datetime, timedelta


class CommentService:
    """Servicios auxiliares para comentarios"""

    # Patrones de spam/simple validación
    SPAM_PATTERNS = [
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        r'(.)\1{5,}',  # Caracteres repetidos más de 5 veces
    ]

    MAX_COMMENT_LENGTH = 2000
    MIN_COMMENT_LENGTH = 3

    @staticmethod
    def validate_comment_text(text: str) -> tuple[bool, Optional[str]]:
        """
        Valida el texto de un comentario.
        Retorna (es_valido, mensaje_error)
        """
        if not text or not text.strip():
            return False, "El comentario no puede estar vacío"

        if len(text) < CommentService.MIN_COMMENT_LENGTH:
            return False, f"El comentario debe tener al menos {CommentService.MIN_COMMENT_LENGTH} caracteres"

        if len(text) > CommentService.MAX_COMMENT_LENGTH:
            return False, f"El comentario no puede exceder los {CommentService.MAX_COMMENT_LENGTH} caracteres"

        # Verificar patrones de spam
        for pattern in CommentService.SPAM_PATTERNS:
            if re.search(pattern, text):
                return False, "El comentario contiene contenido no permitido"

        return True, None

    @staticmethod
    def format_comment_text(text: str) -> str:
        """Formatea el texto del comentario (limpia espacios extra, etc.)"""
        # Eliminar espacios extra al inicio y final
        text = text.strip()
        
        # Reemplazar múltiples espacios con uno solo
        text = re.sub(r' +', ' ', text)
        
        # Reemplazar múltiples saltos de línea con uno solo
        text = re.sub(r'\n+', '\n', text)
        
        return text

    @staticmethod
    def format_date(date: datetime) -> str:
        """Formatea una fecha para mostrar en UI"""
        now = datetime.utcnow()
        diff = now - date

        if diff < timedelta(minutes=1):
            return "Hace un momento"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"Hace {minutes} minuto{'s' if minutes != 1 else ''}"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"Hace {hours} hora{'s' if hours != 1 else ''}"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"Hace {days} día{'s' if days != 1 else ''}"
        elif diff < timedelta(days=30):
            weeks = int(diff.days / 7)
            return f"Hace {weeks} semana{'s' if weeks != 1 else ''}"
        elif diff < timedelta(days=365):
            months = int(diff.days / 30)
            return f"hace {months} mes{'es' if months != 1 else ''}"
        else:
            return date.strftime("%d/%m/%Y")

    @staticmethod
    def escape_html(text: str) -> str:
        """Escapa caracteres HTML para prevenir XSS"""
        replacements = {
            '&': '&',
            '<': '<',
            '>': '>',
            '"': '"',
            "'": '&#x27;',
            '/': '&#x2F;',
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text

    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """Extrae menciones de usuario del texto (@username)"""
        return re.findall(r'@(\w+)', text)

    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """Extrae hashtags del texto"""
        return re.findall(r'#(\w+)', text)

    @staticmethod
    def validate_report_reason(reason: str) -> tuple[bool, Optional[str]]:
        """Valida la razón de un reporte"""
        if not reason or not reason.strip():
            return False, "El motivo del reporte no puede estar vacío"

        if len(reason) < 5:
            return False, "El motivo del reporte debe tener al menos 5 caracteres"

        if len(reason) > 500:
            return False, "El motivo del reporte no puede exceder los 500 caracteres"

        return True, None