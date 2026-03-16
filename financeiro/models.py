# financeiro/models.py
from django.db import models
from veiculos.models import Veiculo
from django.contrib.auth.models import User

# MODEL DE IPVA
class IPVA(models.Model):

    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)

    ano = models.IntegerField()

    valor = models.DecimalField(max_digits=10, decimal_places=2)

    data_vencimento = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("pendente","Pendente"),
            ("pago","Pago")
        ],
        default="pendente"
    )

    comprovante = models.FileField(upload_to="financeiro/ipva/", blank=True, null=True)

    def __str__(self):
        return f"{self.veiculo.placa} - IPVA {self.ano}"


# MODEL DE LICENCIAMENTO
class Licenciamento(models.Model):

    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)

    ano = models.IntegerField()

    valor = models.DecimalField(max_digits=10, decimal_places=2)

    data_vencimento = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("pendente","Pendente"),
            ("pago","Pago")
        ],
        default="pendente"
    )

    comprovante = models.FileField(upload_to="financeiro/licenciamento/", blank=True, null=True)

    def __str__(self):
        return f"{self.veiculo.placa} - Licenciamento {self.ano}"    


# MODEL DE MULTA
class Multa(models.Model):

    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)

    data_infracao = models.DateField()

    descricao = models.CharField(max_length=255)

    valor = models.DecimalField(max_digits=10, decimal_places=2)

    pontos = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("pendente","Pendente"),
            ("pago","Pago"),
            ("recorrido","Recorrido")
        ],
        default="pendente"
    )

    foto_auto = models.ImageField(upload_to="financeiro/multas/", blank=True, null=True)

    def __str__(self):
        return f"{self.veiculo.placa} - {self.valor}"    


# MODEL DE MANUTENÇÃO
class Manutencao(models.Model):

    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)

    descricao = models.CharField(max_length=255)

    valor = models.DecimalField(max_digits=10, decimal_places=2)

    data = models.DateField()

    km = models.IntegerField(null=True, blank=True)

    fornecedor = models.CharField(max_length=120, blank=True)

    comprovante = models.FileField(upload_to="financeiro/manutencao/", blank=True, null=True)

    def __str__(self):
        return f"{self.veiculo.placa} - {self.descricao}"    