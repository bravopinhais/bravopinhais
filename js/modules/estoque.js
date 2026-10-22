export function renderEstoque(state) {
  const container = document.getElementById('content');

  const list = state.db.estoque.filter(item => {
    const busca = state.filters.estoque.busca.toLowerCase();
    const matchesBusca =
      !busca ||
      (item.item || '').toLowerCase().includes(busca) ||
      (item.localizacao || '').toLowerCase().includes(busca);

    const matchesCategoria =
      state.filters.estoque.categoria === 'Todas' || item.categoria === state.filters.estoque.categoria;

    const isCritical = Number(item.qtd) <= Number(item.minimo);
    const matchesStatus =
      state.filters.estoque.status === 'Todos' ||
      (state.filters.estoque.status === 'Critico' && isCritical) ||
      (state.filters.estoque.status === 'OK' && !isCritical);

    return matchesBusca && matchesCategoria && matchesStatus;
  });

  const categorias = [...new Set(state.db.estoque.map(item => item.categoria))];

  container.innerHTML = `
    <section class="section-header">
      <div>
        <h2>Estoque</h2>
        <p>Controle de produtos e níveis críticos</p>
      </div>
    </section>

    <div class="toolbar">
      <input id="estoqueBusca" type="text" placeholder="Buscar produto..." value="${state.filters.estoque.busca}" />
      <select id="estoqueCategoria">
        <option value="Todas" ${state.filters.estoque.categoria === 'Todas' ? 'selected' : ''}>Todas</option>
        ${categorias.map(cat => `<option value="${cat}" ${state.filters.estoque.categoria === cat ? 'selected' : ''}>${cat}</option>`).join('')}
      </select>
      <select id="estoqueStatus">
        <option value="Todos" ${state.filters.estoque.status === 'Todos' ? 'selected' : ''}>Todos</option>
        <option value="Critico" ${state.filters.estoque.status === 'Critico' ? 'selected' : ''}>Crítico</option>
        <option value="OK" ${state.filters.estoque.status === 'OK' ? 'selected' : ''}>Normal</option>
      </select>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Produto</th>
            <th>Categoria</th>
            <th>Quantidade</th>
            <th>Localização</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${list.length === 0 ? '<tr><td colspan="5" class="empty-state">Nenhum item encontrado.</td></tr>' : list.map(item => {
            const critical = Number(item.qtd) <= Number(item.minimo);
            return `
              <tr>
                <td>${item.item}</td>
                <td>${item.categoria}</td>
                <td>${item.qtd} / min ${item.minimo}</td>
                <td>${item.localizacao || 'Almoxarifado'}</td>
                <td>
                  <span class="badge ${critical ? 'badge-danger' : 'badge-success'}">
                    ${critical ? 'Crítico' : 'Normal'}
                  </span>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;

  document.getElementById('estoqueBusca')?.addEventListener('input', (event) => {
    state.filters.estoque.busca = event.target.value;
    renderEstoque(state);
  });

  document.getElementById('estoqueCategoria')?.addEventListener('change', (event) => {
    state.filters.estoque.categoria = event.target.value;
    renderEstoque(state);
  });

  document.getElementById('estoqueStatus')?.addEventListener('change', (event) => {
    state.filters.estoque.status = event.target.value;
    renderEstoque(state);
  });
}
