export function renderMoradores(state) {
  const container = document.getElementById('content');
  const blocos = [...new Set(state.db.moradores.map(item => item.bloco).filter(Boolean))];

  const list = state.db.moradores.filter(item => {
    const busca = state.filters.moradores.busca.toLowerCase();
    const matchesBusca =
      !busca ||
      (item.nome || '').toLowerCase().includes(busca) ||
      (item.apartamento || '').toLowerCase().includes(busca) ||
      (item.email || '').toLowerCase().includes(busca);

    const matchesBloco =
      state.filters.moradores.bloco === 'Todos' || item.bloco === state.filters.moradores.bloco;

    const matchesTipo =
      state.filters.moradores.tipo === 'Todos' || item.tipo === state.filters.moradores.tipo;

    return matchesBusca && matchesBloco && matchesTipo;
  });

  container.innerHTML = `
    <section class="section-header">
      <div>
        <h2>Moradores / unidades</h2>
        <p>Cadastro de moradores e unidades habitacionais</p>
      </div>
    </section>

    <div class="toolbar">
      <input id="moradorBusca" type="text" placeholder="Buscar por nome..." value="${state.filters.moradores.busca}" />
      <select id="moradorBloco">
        <option value="Todos" ${state.filters.moradores.bloco === 'Todos' ? 'selected' : ''}>Todos</option>
        ${blocos.map(bloco => `<option value="${bloco}" ${state.filters.moradores.bloco === bloco ? 'selected' : ''}>${bloco}</option>`).join('')}
      </select>
      <select id="moradorTipo">
        <option value="Todos" ${state.filters.moradores.tipo === 'Todos' ? 'selected' : ''}>Todos</option>
        <option value="Proprietário" ${state.filters.moradores.tipo === 'Proprietário' ? 'selected' : ''}>Proprietário</option>
        <option value="Inquilino" ${state.filters.moradores.tipo === 'Inquilino' ? 'selected' : ''}>Inquilino</option>
      </select>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Nome</th>
            <th>Bloco</th>
            <th>Apartamento</th>
            <th>Tipo</th>
            <th>Email</th>
          </tr>
        </thead>
        <tbody>
          ${list.length === 0 ? '<tr><td colspan="5" class="empty-state">Nenhum morador encontrado.</td></tr>' : list.map(item => `
            <tr>
              <td>${item.nome}</td>
              <td>${item.bloco}</td>
              <td>${item.apartamento}</td>
              <td>${item.tipo}</td>
              <td>${item.email || '-'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  document.getElementById('moradorBusca')?.addEventListener('input', (event) => {
    state.filters.moradores.busca = event.target.value;
    renderMoradores(state);
  });

  document.getElementById('moradorBloco')?.addEventListener('change', (event) => {
    state.filters.moradores.bloco = event.target.value;
    renderMoradores(state);
  });

  document.getElementById('moradorTipo')?.addEventListener('change', (event) => {
    state.filters.moradores.tipo = event.target.value;
    renderMoradores(state);
  });
}
