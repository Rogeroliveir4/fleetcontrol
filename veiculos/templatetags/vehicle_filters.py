# veiculos/templatetags/vehicle_filters.py
from django import template
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta


register = template.Library()

# ========== FILTROS DE CONTAGEM ==========

@register.filter
def count_by_status(queryset, status):
    """Filtra um queryset por status e retorna a contagem"""
    if hasattr(queryset, 'filter'):
        return queryset.filter(status=status).count()
    return 0

@register.filter
def count_available(queryset):
    """Retorna a contagem de veículos disponíveis"""
    return queryset.filter(status="Disponivel").count()

@register.filter
def count_in_transit(queryset):
    """Retorna a contagem de veículos em trânsito"""
    return queryset.filter(status="Em Transito").count()

@register.filter
def count_maintenance(queryset):
    """Retorna a contagem de veículos em manutenção"""
    return queryset.filter(status="Manutencao").count()

@register.filter
def count_reserved(queryset):
    """Retorna a contagem de veículos reservados"""
    return queryset.filter(status="Reservado").count()

@register.filter
def count_by_property_type(queryset, tipo):
    """Filtra por tipo de propriedade"""
    return queryset.filter(tipo_propriedade=tipo).count()

@register.filter
def count_owned(queryset):
    """Conta veículos próprios"""
    return queryset.filter(tipo_propriedade="Proprio").count()

@register.filter
def count_rented(queryset):
    """Conta veículos locados"""
    return queryset.filter(tipo_propriedade="Locado").count()

# ========== FILTROS DE FORMATO ==========

@register.filter
def format_placa(value):
    """Formata a placa no padrão brasileiro: ABC-1D23"""
    if not value:
        return ""
    value = str(value).upper().strip()
    if len(value) >= 4 and '-' not in value:
        return f"{value[:3]}-{value[3:]}"
    return value

@register.filter
def format_km(value):
    """Formata número de KM com separadores de milhar"""
    try:
        if value is None:
            return "0"
        num = int(float(value))
        return f"{num:,.0f}".replace(",", ".") + " km"
    except (ValueError, TypeError):
        return str(value) + " km"

@register.filter
def format_renavam(value):
    """Formata RENAVAM (se houver)"""
    if not value:
        return "Não informado"
    return str(value)

@register.filter
def format_insurance(value):
    """Formata status do seguro"""
    if value:
        return "Ativo"
    return "Inativo"

@register.filter
def format_insurance_date(date):
    """Formata data do seguro com verificação de vencimento"""
    if not date:
        return "Não informado"
    
    today = timezone.now().date()
    if date < today:
        return f"<span class='text-red-600'>{date.strftime('%d/%m/%Y')} (Vencido)</span>"
    elif date <= today + timedelta(days=30):
        return f"<span class='text-yellow-600'>{date.strftime('%d/%m/%Y')} (Próximo)</span>"
    else:
        return f"<span class='text-green-600'>{date.strftime('%d/%m/%Y')}</span>"

@register.filter
def format_license_date(date):
    """Formata data de licenciamento com verificação de vencimento"""
    if not date:
        return "Não informado"
    
    today = timezone.now().date()
    if date < today:
        return f"<span class='text-red-600'>{date.strftime('%d/%m/%Y')} (Vencido)</span>"
    elif date <= today + timedelta(days=30):
        return f"<span class='text-yellow-600'>{date.strftime('%d/%m/%Y')} (Próximo)</span>"
    else:
        return f"<span class='text-green-600'>{date.strftime('%d/%m/%Y')}</span>"

# ========== FILTROS DE STATUS/VISUAL ==========

@register.filter
def status_color(status):
    """Retorna classes CSS baseadas no status"""
    colors = {
        'Disponivel': 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
        'Manutencao': 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
        'Reservado': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300',
        'Em Transito': 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300',
    }
    return colors.get(status, 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300')

@register.filter
def status_icon(status):
    """Retorna ícone baseado no status"""
    icons = {
        'Disponivel': 'fa-check-circle',
        'Manutencao': 'fa-wrench',
        'Reservado': 'fa-clock',
        'Em Transito': 'fa-truck-moving',
    }
    return icons.get(status, 'fa-car')

@register.filter
def property_type_color(tipo):
    """Retorna classes CSS baseadas no tipo de propriedade"""
    colors = {
        'Proprio': 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
        'Locado': 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
    }
    return colors.get(tipo, 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300')

@register.filter
def fuel_type_color(combustivel):
    """Retorna classes CSS baseadas no tipo de combustível"""
    colors = {
        'gasolina': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300',
        'diesel': 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
        'etanol': 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
        'flex': 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
        'eletrico': 'bg-teal-100 dark:bg-teal-900/30 text-teal-800 dark:text-teal-300',
    }
    return colors.get(combustivel, 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300')

@register.filter
def vehicle_icon(tipo):
    """Retorna ícone baseado no tipo de veículo"""
    icons = {
        'carro': 'fa-car',
        'caminhao': 'fa-truck',
        'moto': 'fa-motorcycle',
        'caminhonete': 'fa-truck-pickup',
        'van': 'fa-van-shuttle',
        'onibus': 'fa-bus',
    }
    return icons.get(tipo, 'fa-car')

# ========== FILTROS DE ORDENAÇÃO E FILTRO ==========

@register.filter
def order_by_field(queryset, field):
    """Ordena o queryset por um campo"""
    if hasattr(queryset, 'order_by'):
        return queryset.order_by(field)
    return queryset

@register.filter
def filter_by_field(queryset, condition):
    """Filtra o queryset por uma condição (ex: 'status__Disponivel')"""
    if hasattr(queryset, 'filter'):
        field, value = condition.split('__')
        return queryset.filter(**{field: value})
    return queryset

@register.filter
def search_vehicles(queryset, term):
    """Busca veículos por placa, modelo ou marca"""
    if not term:
        return queryset
    
    if hasattr(queryset, 'filter'):
        return queryset.filter(
            Q(placa__icontains=term) |
            Q(modelo__icontains=term) |
            Q(marca__icontains=term) |
            Q(cor__icontains=term)
        )
    return queryset

# ========== FILTROS DE RESUMO/DASHBOARD ==========

@register.filter
def upcoming_documents(queryset, days=30):
    """Retorna veículos com documentos próximos do vencimento"""
    today = timezone.now().date()
    future_date = today + timedelta(days=days)
    
    return queryset.filter(
        Q(licenciamento_vencimento__range=[today, future_date]) |
        Q(seguro_validade__range=[today, future_date])
    ).distinct()

@register.filter
def expired_documents(queryset):
    """Retorna veículos com documentos vencidos"""
    today = timezone.now().date()
    
    return queryset.filter(
        Q(licenciamento_vencimento__lt=today) |
        Q(seguro_validade__lt=today)
    ).distinct()

@register.filter
def high_mileage_vehicles(queryset, threshold=100000):
    """Retorna veículos com alta quilometragem"""
    return queryset.filter(km_atual__gte=threshold)

@register.filter
def low_fuel_efficiency(queryset, threshold=8):
    """Filtra veículos por baixa eficiência (KM/L) - se tiver esse campo"""
    try:
        return queryset.filter(media_km_litro__lte=threshold)
    except:
        return queryset.none()

# ========== FILTROS DE AGRUPAMENTO ==========

@register.filter
def group_by_status(queryset):
    """Agrupa veículos por status"""
    if hasattr(queryset, 'values'):
        return queryset.values('status').annotate(total=Count('id')).order_by('-total')
    return []

@register.filter
def group_by_type(queryset):
    """Agrupa veículos por tipo"""
    if hasattr(queryset, 'values'):
        return queryset.values('tipo').annotate(total=Count('id')).order_by('-total')
    return []

@register.filter
def group_by_brand(queryset):
    """Agrupa veículos por marca"""
    if hasattr(queryset, 'values'):
        return queryset.values('marca').annotate(total=Count('id')).order_by('-total')
    return []

# ========== FILTROS DE TESTE/VERIFICAÇÃO ==========

@register.filter
def has_document_expired(date):
    """Verifica se uma data está vencida"""
    if not date:
        return False
    return date < timezone.now().date()

@register.filter
def is_document_near_expiry(date, days=30):
    """Verifica se uma data está próxima do vencimento"""
    if not date:
        return False
    today = timezone.now().date()
    future_date = today + timedelta(days=days)
    return today <= date <= future_date

@register.filter
def needs_maintenance(km_atual, last_maintenance_km, interval=10000):
    """Verifica se o veículo precisa de manutenção baseado na KM"""
    try:
        km_atual = int(km_atual)
        last_maintenance_km = int(last_maintenance_km)
        return km_atual - last_maintenance_km >= interval
    except:
        return False

# ========== FILTROS ÚTEIS GERAIS ==========

@register.filter
def get_item(dictionary, key):
    """Acessa um item de um dicionário por chave"""
    return dictionary.get(key)

@register.filter
def split_string(value, delimiter=','):
    """Divide uma string por delimitador"""
    if not value:
        return []
    return [item.strip() for item in str(value).split(delimiter)]

@register.filter
def first_word(value):
    """Retorna a primeira palavra de uma string"""
    if not value:
        return ""
    return str(value).split()[0]

@register.filter
def limit_chars(value, max_chars=50):
    """Limita o número de caracteres e adiciona '...' se necessário"""
    if not value:
        return ""
    value = str(value)
    if len(value) > max_chars:
        return value[:max_chars] + "..."
    return value


@register.filter
def brnum(value):
    try:
        value = int(value)
    except:
        return value

    formatted = f"{value:,}"  # formato americano 745,698
    return formatted.replace(",", ".")  # brasileiro 745.698


# ========== REGISTRO DA BIBLIOTECA ==========

# Para usar no template:
# {% load vehicle_filters %}
# 
# Exemplos de uso:
# 1. {{ veiculos|count_by_status:"Disponivel" }}
# 2. {{ veiculo.placa|format_placa }}
# 3. {{ veiculo.km_atual|format_km }}
# 4. {{ veiculo.status|status_color }}
# 5. {{ veiculo.tipo|vehicle_icon }}