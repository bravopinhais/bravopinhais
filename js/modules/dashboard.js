import { formatCurrency } from '../js/utils.js';

export function renderDashboard(state) {
  const container = document.getElementById('content');

  const receitas = state.db.financeiro
    .filter(item => item.tipo === 'Receber' && item.status === 'Baixado')
    .reduce((sum, item) => sum + Number(item.valor || 0), 0);

  const despesas = state.db.financeiro
    .filter(item => item.tipo === 'Pagar' && item.status === 'Baixado')
    .reduce((sum, item) => sum + Number(item.valor || 0), 0);

  const abertas = state.db.financeiro
    .filter(item => item.status === 'Aberto')
    .reduce((sum, item) => sum + Number(item.valor || 0), 0);

  container.innerHTML = `
    <section class="section-header">
      <div>
        <h2>Dashboard</h2>
        <p>Resumo geral da administração</p>
      </div>
    </section>

    <div class="stats-grid">
      <div class="stat-card success">
        <span>Receitas liquidadas</span>
        <strong>${formatCurrency(receitas)}</strong>
      </div>
      <div class="stat-card danger">
        <span>Despesas liquidadas</span>
        <strong>${formatCurrency(despesas)}</strong>
      </div>
      <div class="stat-card warning">
        <span>Valores em aberto</span>
        <strong>${formatCurrency(abertas)}</strong>
      </div>
      <div class="stat-card info">
        <span>Saldo operacional</span>
        <strong>${formatCurrency(receitas - despesas)}</strong>
      </div>
    </div>
  `;
}
