#!/usr/bin/env python3
"""
fix-accents.py — Portuguese accent correction for newsletter editions.

Fixes missing diacritical marks (acentos) in Portuguese text.
Only operates on visible text content inside HTML tags (not attributes, URLs, or CSS classes).

Usage:
    python scripts/fix-accents.py editions/2026-03-13.html [--dry-run]

Options:
    --dry-run   Show what would be changed without modifying the file.
"""
import re
import sys
from pathlib import Path

# ============================================================
# Portuguese word corrections: unaccented → accented
# ============================================================
# Only include words where the unaccented form is NEVER valid in Portuguese.
# Organized by frequency of appearance in O&G/Mining newsletters.

ACCENT_FIXES = {
    # -ção / -ções (most common missing accent pattern)
    'producao': 'produção', 'producoes': 'produções',
    'mineracao': 'mineração',
    'arrecadacao': 'arrecadação',
    'operacao': 'operação', 'operacoes': 'operações',
    'participacao': 'participação', 'participacoes': 'participações',
    'negociacao': 'negociação', 'negociacoes': 'negociações',
    'situacao': 'situação', 'situacoes': 'situações',
    'informacao': 'informação', 'informacoes': 'informações',
    'projecao': 'projeção', 'projecoes': 'projeções',
    'regulacao': 'regulação',
    'exploracao': 'exploração',
    'perfuracao': 'perfuração',
    'distribuicao': 'distribuição',
    'transicao': 'transição',
    'inovacao': 'inovação',
    'tributacao': 'tributação',
    'legislacao': 'legislação',
    'descomissionamento': 'descomissionamento',  # no accent needed
    'licitacao': 'licitação', 'licitacoes': 'licitações',
    'concessao': 'concessão', 'concessoes': 'concessões',
    'exportacao': 'exportação', 'exportacoes': 'exportações',
    'importacao': 'importação', 'importacoes': 'importações',
    'instalacao': 'instalação', 'instalacoes': 'instalações',
    'manutencao': 'manutenção',
    'reparacao': 'reparação', 'reparacoes': 'reparações',
    'avaliacao': 'avaliação', 'avaliacoes': 'avaliações',
    'certificacao': 'certificação', 'certificacoes': 'certificações',
    'estimacao': 'estimação',
    'cotacao': 'cotação', 'cotacoes': 'cotações',
    'movimentacao': 'movimentação',
    'recuperacao': 'recuperação',
    'atuacao': 'atuação',
    'geracao': 'geração',
    'transmissao': 'transmissão',
    'compensacao': 'compensação',
    'liquidacao': 'liquidação',
    'publicacao': 'publicação', 'publicacoes': 'publicações',
    'resolucao': 'resolução', 'resolucoes': 'resoluções',
    'obrigacao': 'obrigação', 'obrigacoes': 'obrigações',
    'aquisicao': 'aquisição', 'aquisicoes': 'aquisições',
    'contratacao': 'contratação', 'contratacoes': 'contratações',
    'consolidacao': 'consolidação',
    'construcao': 'construção',
    'recomendacao': 'recomendação', 'recomendacoes': 'recomendações',
    'aceleracao': 'aceleração',
    'ampliacao': 'ampliação',
    'aplicacao': 'aplicação',
    'completacao': 'completação', 'completacoes': 'completações',
    'equacao': 'equação',
    'exposicao': 'exposição',
    'formacao': 'formação',
    'implicacao': 'implicação',
    'inflacao': 'inflação',
    'judicializacao': 'judicialização',
    'liberacao': 'liberação', 'liberacoes': 'liberações',
    'navegacao': 'navegação',
    'reducao': 'redução', 'reducoes': 'reduções',
    'relacao': 'relação',
    'remuneracao': 'remuneração',
    'restricao': 'restrição',
    'retencao': 'retenção',
    'revitalizacao': 'revitalização',
    'valoracao': 'valoração',
    'automacao': 'automação',
    'federacao': 'federação',
    'associacao': 'associação',
    'apresentacoes': 'apresentações',
    'inscricoes': 'inscrições',
    'convencoes': 'convenções',
    'eleicoes': 'eleições',

    # -ão / -ões
    'leilao': 'leilão', 'leiloes': 'leilões',
    'pressao': 'pressão', 'pressoes': 'pressões',
    'expansao': 'expansão', 'expansoes': 'expansões',
    'regiao': 'região', 'regioes': 'regiões',
    'orgao': 'órgão', 'orgaos': 'órgãos',
    'reuniao': 'reunião', 'reunioes': 'reuniões',
    'revisao': 'revisão', 'revisoes': 'revisões',
    'dimensao': 'dimensão',
    'previsao': 'previsão', 'previsoes': 'previsões',
    'decisao': 'decisão', 'decisoes': 'decisões',
    'emissao': 'emissão', 'emissoes': 'emissões',
    'posicao': 'posição', 'posicoes': 'posições',
    'condicao': 'condição', 'condicoes': 'condições',
    'reversao': 'reversão',

    # -éu / -óleo / -ário
    'petroleo': 'petróleo',
    'regulatorio': 'regulatório', 'regulatoria': 'regulatória',
    'salario': 'salário', 'salarios': 'salários',
    'calendario': 'calendário',
    'necessario': 'necessário', 'necessaria': 'necessária',
    'voluntario': 'voluntário', 'voluntarios': 'voluntários',
    'monetario': 'monetário', 'monetaria': 'monetária',
    'tributario': 'tributário', 'tributaria': 'tributária',
    'orçamentario': 'orçamentário',
    'orcamento': 'orçamento',

    # -ético / -ático / -ístico
    'geopolitica': 'geopolítica', 'geopolitico': 'geopolítico',
    'estrategica': 'estratégica', 'estrategico': 'estratégico',
    'eletrica': 'elétrica', 'eletrico': 'elétrico',
    'energetica': 'energética', 'energetico': 'energético',
    'logistica': 'logística', 'logistico': 'logístico',
    'estatistica': 'estatística',

    # -ís / -ês / -ções
    'pais': 'país', 'paises': 'países',

    # -eço / -eça
    'preco': 'preço', 'precos': 'preços',

    # -ízo / -ício
    'prejuizo': 'prejuízo', 'prejuizos': 'prejuízos',
    'exercicio': 'exercício', 'exercicios': 'exercícios',
    'inicio': 'início',
    'beneficio': 'benefício', 'beneficios': 'benefícios',

    # -íodo / -ério
    'periodo': 'período', 'periodos': 'períodos',
    'criterio': 'critério', 'criterios': 'critérios',

    # -índice / -ônus
    'indice': 'índice', 'indices': 'índices',
    'bonus': 'bônus',

    # -ência / -ância
    'potencia': 'potência',
    'consequencia': 'consequência',
    'tendencia': 'tendência', 'tendencias': 'tendências',
    'emergencia': 'emergência',
    'referencia': 'referência', 'referencias': 'referências',
    'frequencia': 'frequência',
    'eficiencia': 'eficiência',
    'experiencia': 'experiência',
    'transferencia': 'transferência',
    'concorrencia': 'concorrência',
    'importancia': 'importância',
    'tolerancia': 'tolerância',
    'substancia': 'substância', 'substancias': 'substâncias',

    # -órico / -áximo / -ínimo
    'historico': 'histórico', 'historica': 'histórica',
    'maximo': 'máximo', 'maxima': 'máxima',
    'minimo': 'mínimo', 'minima': 'mínima',

    # -álise / -ível / -édito
    'analise': 'análise', 'analises': 'análises',
    'possivel': 'possível',
    'credito': 'crédito', 'creditos': 'créditos',
    'numero': 'número', 'numeros': 'números',

    # -ático
    'automatico': 'automático', 'automatica': 'automática',
    'climatico': 'climático', 'climatica': 'climática',

    # -ência / -ância (more)
    'ausencia': 'ausência',
    'transparencia': 'transparência',
    'vivencia': 'vivência',
    'conferencia': 'conferência',
    'agencia': 'agência',
    'diretoria': 'diretoria',  # no accent — correct as is
    'consultoria': 'consultoria',  # no accent — correct as is
    'curadoria': 'curadoria',  # no accent — correct as is

    # -ório / -ória (more)
    'territorio': 'território',
    'relatorio': 'relatório',

    # -ável / -ível / -ível
    'disponivel': 'disponível',
    'comparavel': 'comparável',
    'sustentavel': 'sustentável',
    'saudavel': 'saudável',
    'instavel': 'instável',
    'nivel': 'nível',

    # Specific O&G / Mining words
    'oleo': 'óleo',
    'residuos': 'resíduos',
    'acao': 'ação',
    'acoes': 'ações',
    'historia': 'história',
    'proxima': 'próxima', 'proximo': 'próximo',
    'proximos': 'próximos', 'proximas': 'próximas',
    'America': 'América',
    'litio': 'lítio',
    'niobio': 'nióbio',
    'gas': 'gás',
    'pocos': 'poços',
    'carvao': 'carvão',
    'combustiveis': 'combustíveis',
    'licenca': 'licença',
    'presenca': 'presença',

    # Common words — accents often missing
    'nao': 'não',
    'sao': 'são',
    'tambem': 'também',
    'ate': 'até',
    'apos': 'após',
    'alem': 'além',
    'ja': 'já',
    'so': 'só',
    'pos': 'pós',
    'pre': 'pré',
    'tres': 'três',
    'agua': 'água', 'aguas': 'águas',
    'area': 'área', 'areas': 'áreas',
    'liquida': 'líquida', 'liquido': 'líquido',
    'tercos': 'terços',
    'vies': 'viés',
    'volatil': 'volátil',
    'deficit': 'déficit',
    'superavit': 'superávit',
    'edicao': 'edição', 'edicoes': 'edições',
    'diagnostico': 'diagnóstico',
    'simbolo': 'símbolo', 'simbolos': 'símbolos',
    'unico': 'único', 'unica': 'única',
    'publico': 'público', 'publica': 'pública',
    'tecnico': 'técnico', 'tecnica': 'técnica',
    'economico': 'econômico', 'economica': 'econômica',
    'especifico': 'específico', 'especifica': 'específica',
    'politica': 'política', 'politico': 'político',
    'domestico': 'doméstico', 'domestica': 'doméstica',
    'hidrico': 'hídrico', 'hidrica': 'hídrica',
    'hidreletrica': 'hidrelétrica',
    'termoeletrica': 'termoelétrica',
    'termeletrica': 'termelétrica', 'termeletricas': 'termelétricas',
    'eolica': 'eólica',
    'util': 'útil',
    'multiplos': 'múltiplos', 'multiplas': 'múltiplas',
    'mantem': 'mantém',
    'estao': 'estão',
    'podera': 'poderá',
    'Brasilia': 'Brasília',
    'Uniao': 'União',
    'Japao': 'Japão',
    'India': 'Índia',
    'Cazaquistao': 'Cazaquistão',
    'Medio': 'Médio',  # Médio Oriente
    'niveis': 'níveis',
    'cenario': 'cenário', 'cenarios': 'cenários',
    'tematico': 'temático', 'tematica': 'temática',
    'dinamica': 'dinâmica', 'dinamico': 'dinâmico',
    'maritima': 'marítima', 'maritimo': 'marítimo',
    'diaria': 'diária', 'diario': 'diário', 'diarias': 'diárias',
    'temporario': 'temporário', 'temporaria': 'temporária',
    'oceanica': 'oceânica', 'oceanico': 'oceânico',
    'periferica': 'periférica', 'perifericas': 'periféricas',
    'cetico': 'cético',
    'tensao': 'tensão',
    'agronegocio': 'agronegócio',
    'reforca': 'reforça',
    'avancando': 'avançando', 'avanco': 'avanço',
    'bilhoes': 'bilhões',
    'milhoes': 'milhões',
    'trilhoes': 'trilhões',
    'industria': 'indústria',
    'estrategia': 'estratégia',
    'negocios': 'negócios',
    'pratico': 'prático', 'pratica': 'prática',
    'Furia': 'Fúria',
    'Epica': 'Épica',
}

# ============================================================
# HTML-aware accent correction
# ============================================================

def fix_accents_in_text(text_content):
    """Fix accents in a text string (not HTML-aware — use on text nodes only)."""
    fixed = text_content
    count = 0
    for wrong, correct in ACCENT_FIXES.items():
        # Case-sensitive match for lowercase
        pattern = r'\b' + re.escape(wrong) + r'\b'
        matches = len(re.findall(pattern, fixed))
        if matches:
            fixed = re.sub(pattern, correct, fixed)
            count += matches

        # Title case (e.g., "Producao" → "Produção")
        wrong_title = wrong[0].upper() + wrong[1:]
        correct_title = correct[0].upper() + correct[1:]
        pattern_title = r'\b' + re.escape(wrong_title) + r'\b'
        matches_title = len(re.findall(pattern_title, fixed))
        if matches_title:
            fixed = re.sub(pattern_title, correct_title, fixed)
            count += matches_title

        # ALL CAPS (e.g., "PRODUCAO" → "PRODUÇÃO")
        wrong_upper = wrong.upper()
        correct_upper = correct.upper()
        pattern_upper = r'\b' + re.escape(wrong_upper) + r'\b'
        matches_upper = len(re.findall(pattern_upper, fixed))
        if matches_upper:
            fixed = re.sub(pattern_upper, correct_upper, fixed)
            count += matches_upper

    return fixed, count


def fix_accents_in_html(html_content):
    """Fix accents only in visible text content of HTML, not in tags/attributes/URLs."""
    total_fixes = 0

    def replace_text_node(match):
        nonlocal total_fixes
        text = match.group(0)
        fixed, count = fix_accents_in_text(text)
        total_fixes += count
        return fixed

    # Match text between HTML tags (not inside < > and not inside href/src attributes)
    # Strategy: split by tags, fix text parts only
    parts = re.split(r'(<[^>]+>)', html_content)
    result = []
    for part in parts:
        if part.startswith('<'):
            # Inside a tag — only fix text in title/alt attributes if needed
            result.append(part)
        else:
            # Text node — fix accents
            fixed, count = fix_accents_in_text(part)
            total_fixes += count
            result.append(fixed)

    return ''.join(result), total_fixes


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix-accents.py <html-file> [--dry-run]")
        print("       python scripts/fix-accents.py editions/2026-03-13.html")
        print("       python scripts/fix-accents.py editions/2026-03-13.html --dry-run")
        sys.exit(1)

    html_path = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv

    if not html_path.exists():
        print(f"Error: {html_path} not found")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if dry_run else ''}Fixing accents in: {html_path}")

    original = html_path.read_text(encoding='utf-8')
    fixed, count = fix_accents_in_html(original)

    if count == 0:
        print("No accent issues found. File is clean!")
        return

    print(f"Fixed {count} accent issues.")

    if dry_run:
        # Show diff-like output
        orig_lines = original.splitlines()
        fixed_lines = fixed.splitlines()
        changes_shown = 0
        for i, (orig, fix) in enumerate(zip(orig_lines, fixed_lines)):
            if orig != fix:
                changes_shown += 1
                if changes_shown <= 30:
                    print(f"  Line {i+1}:")
                    # Highlight differences
                    print(f"    - {orig.strip()[:120]}")
                    print(f"    + {fix.strip()[:120]}")
        if changes_shown > 30:
            print(f"  ... and {changes_shown - 30} more lines changed")
        print(f"\nTotal: {count} fixes in {changes_shown} lines. Use without --dry-run to apply.")
    else:
        html_path.write_text(fixed, encoding='utf-8')
        print(f"File updated: {html_path}")


if __name__ == '__main__':
    main()
