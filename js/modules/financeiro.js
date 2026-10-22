import { formatCurrency } from '../utils.js';

export function renderFinanceiro(state) {
  const container = document.getElementById('content');

  const list = state.db.financeiro.filter(item => {
    const busca = state.filters.financeiro.busca.toLowerCase();
    const matchesBusca =
      !busca ||
      (item.historico || '').toLowerCase().includes(busca) ||
      (item.fornecedor || '').toLowerCase().includes(busca);

    const matchesStatus =
      state.filters.financeiro.status === 'Todos' || item.status === state.filters.financeiro.status;

    const matchesTipo =
      state.filters.financeiro.tipo === 'Todos' || item.tipo === state.filters.financeiro.tipo;

    return matchesBusca && matchesStatus && matchesTipo;
  });

  container.innerHTML = `
    <section class="section-header">
      <div>
        <h2>Contas a pagar / receber</h2>
        <p>Controle financeiro do condomínio</p>
      </div>
    </section>

    <div class="toolbar">
      <input id="financeiroBusca" type="text" placeholder="Buscar por descrição..." value="${state.filters.financeiro.busca}" />
      <select id="financeiroStatus">
        <option value="Todos" ${state.filters.financeiro.status === 'Todos' ? 'selected' : ''}>Todos</option>
        <option value="Aberto" ${state.filters.financeiro.status === 'Aberto' ? 'selected' : ''}>Aberto</option>
        <option value="Baixado" ${state.filters.financeiro.status === 'Baixado' ? 'selected' : ''}>Baixado</option>
      </select>
      <select id="financeiroTipo">
        <option value="Todos" ${state.filters.financeiro.tipo === 'Todos' ? 'selected' : ''}>Todos</option>
        <option value="Receber" ${state.filters.financeiro.tipo === 'Receber' ? 'selected' : ''}>Receber</option>
        <option value="Pagar" ${state.filters.financeiro.tipo === 'Pagar' ? 'selected' : ''}>Pagar</option>
      </select>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Histórico</th>
            <th>Vencimento</th>
            <th>Valor</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${list.length === 0 ? '<tr><td colspan="5" class="empty-state">Nenhum registro encontrado.</td></tr>' : list.map(item => `
            <tr>
              <td>
                <span class="badge ${item.tipo === 'Receber' ? 'badge-success' : 'badge-danger'}">
                  ${item.tipo}
                </span>
              </td>
              <td>${item.historico}</td>
              <td>${item.vencimento}</td>
              <td>${formatCurrency(item.valor)}</td>
              <td>
                <span class="badge ${item.status === 'Baixado' ? 'badge-success' : 'badge-warning'}">
                  ${item.status}
                </span>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  document.getElementById('financeiroBusca')?.addEventListener('input', (event) => {
    state.filters.financeiro.busca = event.target.value;
    renderFinanceiro(state);
  });

  document.getElementById('financeiroStatus')?.addEventListener('change', (event) => {
    state.filters.financeiro.status = event.target.value;
    renderFinanceiro(state);
  });

  document.getElementById('financeiroTipo')?.addEventListener('change', (event) => {
    state.filters.financeiro.tipo = event.target.value;
    renderFinanceiro(state);
  });
}
