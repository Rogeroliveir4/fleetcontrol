import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Contrato

def lista_contratos(request):
    search = request.GET.get("search", "")

    contratos = Contrato.objects.all()

    if search:
        contratos = contratos.filter(
            Q(nome__icontains=search) |
            Q(cliente__icontains=search) |
            Q(id__icontains=search)
        )

    return render(request, "contratos/lista.html", {
        "contratos": contratos,
        "search": search,
    })


@csrf_exempt  # Temporariamente para testes
def buscar_contratos(request):
    """Retorna todos os contratos ativos em formato JSON"""
    print("=== REQUISIÇÃO PARA BUSCAR CONTRATOS ===")
    print(f"Método: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    
    try:
        contratos = Contrato.objects.filter(ativo=True).order_by('nome')
        print(f"Total de contratos encontrados: {contratos.count()}")
        
        # Listar os contratos encontrados
        for c in contratos:
            print(f"  - {c.id}: {c.nome}")
        
        data = {
            'success': True,
            'contratos': [
                {
                    'id': contrato.id,
                    'nome': contrato.nome or '',
                    'cliente': contrato.cliente or '',
                    'localizacao': contrato.localizacao or '',
                    'ativo': contrato.ativo
                }
                for contrato in contratos
            ]
        }
        
        print(f"Dados retornados: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return JsonResponse(data)
        
    except Exception as e:
        print(f"Erro: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'contratos': []
        })