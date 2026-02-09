from agent.models import Food
from agent.ai_parser import gerar_lista_compras

dieta = [
    Food("arroz", 3000),
    Food("frango", 1500),
]

estoque = []

resultado = gerar_lista_compras(dieta, estoque)

print(resultado)
