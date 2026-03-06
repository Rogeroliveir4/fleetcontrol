from django import forms
from .models import Veiculo

class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = "__all__"

        widgets = {
            "ipva_vencimento": forms.DateInput(attrs={"type": "date"}),
            "licenciamento_vencimento": forms.DateInput(attrs={"type": "date"}),
            "seguro_validade": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_placa(self):
        placa = self.cleaned_data.get('placa', '').upper().strip()
        
        # Verifica se já existe (exceto se estiver editando)
        if self.instance.pk:  # Se estiver editando
            qs = Veiculo.objects.exclude(pk=self.instance.pk)
        else:  # Se for novo
            qs = Veiculo.objects.all()
            
        placa_clean = placa.replace('-', '').replace(' ', '')
        
        if qs.filter(placa__iregex=r'^{}$|^{}$'.format(placa, placa_clean)).exists():
            raise forms.ValidationError('Esta placa já está cadastrada.')
        
        return placa
    
    def clean_tag_interna(self):
        tag_interna = self.cleaned_data.get('tag_interna', '').strip()
        
        if self.instance.pk:
            qs = Veiculo.objects.exclude(pk=self.instance.pk)
        else:
            qs = Veiculo.objects.all()
            
        if qs.filter(tag_interna__iexact=tag_interna).exists():
            raise forms.ValidationError('Esta tag interna já está em uso.')
        
        return tag_interna