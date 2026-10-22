export function renderRelatorios(state) {
  const container = document.getElementById('content');

  const receitas = state.db.financeiro
    .filter(item => item.tipo === 'Receber' && item.status === 'Baixado')
    .reduce((sum, item) => sum + Number(item.valor || 0), 0);

  const despesas = state.db.financeiro
    .filter(item => item.tipo === 'Pagar' && item.status === 'Baixado')
    .reduce((sum, item) => sum + Number(item.valor || 0), 0);

  const itensCriticos = state.db.estoque.filter(item => Number(item.qtd) <= Number(item.minimo));

  container.innerHTML = `
    <section class="section-header">
      <div>
        <h2>Relatórios e DRE</h2>
        <p>Indicadores consolidados e dados operacionais</p>
      </div>
    </section>

    <div class="stats-grid">
      <div class="stat-card success">
        <span>Receita líquida</span>
        <strong>R$ ${receitas.toFixed(2)}</strong>
      </div>
      <div class="stat-card danger">
        <span>Despesa operacional</span>
        <strong>R$ ${despesas.toFixed(2)}</strong>
      </div>
      <div class="stat-card warning">
        <span>Itens críticos</span>
        <strong>${itensCriticos.length}</strong>
      </div>
      <div class="stat-card info">
        <span>Resultado</span>
        <strong>R$ ${(receitas - despesas).toFixed(2)}</strong>
      </div>
    </div>
  `;
}
