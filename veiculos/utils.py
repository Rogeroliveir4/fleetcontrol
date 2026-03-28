# veiculos/utils.py

import re

def validar_placa(placa):
    """
    Valida placa nos formatos:
    - Padrão antigo: ABC-1234
    - Mercosul: ABC1D23 (3 letras, 1 número, 1 letra, 2 números)
    """
    if not placa:
        return False, "Placa não informada"
    
    placa = placa.upper().strip()
    
    # Remover hífens e espaços para verificação
    placa_sem_hifen = placa.replace("-", "").replace(" ", "")
    
    # Formato antigo: ABC-1234
    padrao_antigo = re.compile(r'^[A-Z]{3}-\d{4}$')
    if padrao_antigo.match(placa):
        return True, placa
    
    # Formato antigo sem hífen: ABC1234
    padrao_antigo_sem_hifen = re.compile(r'^[A-Z]{3}\d{4}$')
    if padrao_antigo_sem_hifen.match(placa):
        return True, f"{placa[:3]}-{placa[3:]}"
    
    # Formato Mercosul: ABC1D23 (3 letras, 1 número, 1 letra, 2 números)
    padrao_mercosul = re.compile(r'^[A-Z]{3}\d[A-Z]\d{2}$')
    if padrao_mercosul.match(placa_sem_hifen):
        return True, placa_sem_hifen
    
    # Formato Mercosul com hífen: ABC-1D23
    padrao_mercosul_com_hifen = re.compile(r'^[A-Z]{3}-\d[A-Z]\d{2}$')
    if padrao_mercosul_com_hifen.match(placa):
        return True, placa.replace("-", "")
    
    return False, f"Placa inválida. Formatos aceitos: ABC-1234 (antigo) ou ABC1D23 (Mercosul)"


def formatar_placa(placa):
    """
    Formata placa para exibição:
    - Antigo: ABC-1234
    - Mercosul: ABC-1D23
    """
    placa = placa.upper().strip().replace(" ", "")
    
    # Se já tem hífen e formato antigo, mantém
    if re.match(r'^[A-Z]{3}-\d{4}$', placa):
        return placa
    
    # Se é Mercosul (AAA1A11), formata com hífen após as 3 primeiras letras
    if re.match(r'^[A-Z]{3}\d[A-Z]\d{2}$', placa):
        return f"{placa[:3]}-{placa[3:]}"
    
    # Se é antigo sem hífen (ABC1234), adiciona hífen
    if re.match(r'^[A-Z]{3}\d{4}$', placa):
        return f"{placa[:3]}-{placa[3:]}"
    
    # Se é Mercosul com hífen (ABC-1D23), normaliza
    if re.match(r'^[A-Z]{3}-\d[A-Z]\d{2}$', placa):
        return placa
    
    return placa


def obter_tipo_placa(placa):
    """
    Identifica o tipo da placa
    """
    placa = placa.upper().strip().replace("-", "")
    
    if re.match(r'^[A-Z]{3}\d{4}$', placa):
        return "antigo"
    elif re.match(r'^[A-Z]{3}\d[A-Z]\d{2}$', placa):
        return "mercosul"
    else:
        return "desconhecido"