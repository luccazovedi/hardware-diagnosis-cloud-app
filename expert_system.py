# expert_system.py
# Sistema especialista simples para diagnóstico de hardware

from typing import List, Dict, Set


class HardwareExpertSystem:
    """
    Sistema especialista baseado em regras simples.
    Entrada: conjunto de sintomas selecionados pelo usuário.
    Saída: lista de possíveis diagnósticos e recomendações.
    """

    def __init__(self) -> None:
        # Cada regra tem:
        # - condicoes: conjunto de sintomas necessários
        # - diagnostico: texto descritivo
        # - causa_provavel: explicação
        # - recomendacao: ação sugerida
        self.rules = [
            {
                "condicoes": {"nao_liga"},
                "diagnostico": "Computador não liga",
                "causa_provavel": "Possível problema na fonte de alimentação, cabo de energia ou botão power.",
                "recomendacao": (
                    "Verifique se o cabo está conectado, teste em outra tomada, "
                    "confira a chave de tensão da fonte e, se possível, teste com outra fonte."
                ),
            },
            {
                "condicoes": {"reinicia_sozinho", "superaquecendo"},
                "diagnostico": "Reinicializações devido a superaquecimento",
                "causa_provavel": "Temperatura alta de CPU ou GPU causando desligamento de segurança.",
                "recomendacao": (
                    "Limpe ventoinhas e dissipadores, verifique se os coolers estão girando, "
                    "troque a pasta térmica se necessário e garanta boa circulação de ar no gabinete."
                ),
            },
            {
                "condicoes": {"lento", "uso_disco_alto"},
                "diagnostico": "Desempenho lento por gargalo em disco",
                "causa_provavel": "Disco rígido antigo, quase cheio ou com muitos acessos simultâneos.",
                "recomendacao": (
                    "Considere usar um SSD, liberar espaço em disco, desinstalar programas desnecessários "
                    "e verificar programas iniciando junto com o sistema."
                ),
            },
            {
                "condicoes": {"lento", "pouca_memoria"},
                "diagnostico": "Desempenho lento por falta de memória RAM",
                "causa_provavel": "Aplicativos consumindo mais RAM do que o disponível.",
                "recomendacao": (
                    "Feche programas em segundo plano, aumente a quantidade de RAM "
                    "ou use versões mais leves dos aplicativos."
                ),
            },
            {
                "condicoes": {"sem_video"},
                "diagnostico": "Sem vídeo na tela",
                "causa_provavel": "Problemas na placa de vídeo, cabo de vídeo ou monitor.",
                "recomendacao": (
                    "Teste com outro cabo/monitor, verifique se a placa de vídeo está bem encaixada, "
                    "e teste a saída de vídeo onboard (se houver)."
                ),
            },
            {
                "condicoes": {"ruidos"},
                "diagnostico": "Ruídos estranhos (cliques/chiados)",
                "causa_provavel": "Possível falha em HD mecânico ou ventoinhas desgastadas.",
                "recomendacao": (
                    "Faça backup imediato dos dados, verifique a origem do ruído e considere trocar o componente."
                ),
            },
        ]

    def diagnose(self, symptoms: List[str]) -> List[Dict[str, str]]:
        """
        Recebe lista de sintomas (strings) e retorna lista de diagnósticos.
        """
        symptom_set: Set[str] = set(symptoms)
        resultados: List[Dict[str, str]] = []

        for rule in self.rules:
            condicoes = rule["condicoes"]
            if condicoes.issubset(symptom_set):
                resultados.append(
                    {
                        "diagnostico": rule["diagnostico"],
                        "causa_provavel": rule["causa_provavel"],
                        "recomendacao": rule["recomendacao"],
                    }
                )

        if not resultados:
            resultados.append(
                {
                    "diagnostico": "Nenhuma causa específica identificada",
                    "causa_provavel": (
                        "Os sintomas informados não bateram com nenhuma regra específica do sistema especialista."
                    ),
                    "recomendacao": (
                        "Verifique se os sintomas foram descritos corretamente, "
                        "atualize drivers e sistema operacional, e se o problema persistir, "
                        "considere uma análise mais detalhada por um técnico."
                    ),
                }
            )

        return resultados
