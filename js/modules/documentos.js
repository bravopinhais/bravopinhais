import { formatCurrency } from '../utils.js';

export function renderDocumentos(state) {
  const container = document.getElementById('content');
  const pastas = [...new Set(state.db.categorias.filter(c => c.modulo === 'Documentos' || c.modulo === 'Geral').map(c => c.nome))];

  const list = state.db.documentos.filter(item => {
    const busca = state.filters.documentos.busca.toLowerCase();
    const matchesBusca =
      !busca ||
      (item.titulo || '').toLowerCase().includes(busca) ||
      (item.observacao || '').toLowerCase().includes(busca);

    const matchesPasta =
      state.filters.documentos.pasta === 'Todas' || item.pasta === state.filters.documentos.pasta;

    const matchesIni = !state.filters.documentos.dataIni || item.data >= state.filters.documentos.dataIni;
    const matchesFim = !state.filters.documentos.dataFim || item.data <= state.filters.documentos.dataFim;

    return matchesBusca && matchesPasta && matchesIni && matchesFim;
  });

  container.innerHTML = `
    <section class="section-header">
      <div>
        <h2>Gestão de documentos</h2>
        <p>Pastas, arquivos e registros de documentos</p>
      </div>
    </section>

    <div class="toolbar">
      <input id="docBusca" type="text" placeholder="Buscar por título..." value="${state.filters.documentos.busca}" />
      <select id="docPasta">
        <option value="Todas" ${state.filters.documentos.pasta === 'Todas' ? 'selected' : ''}>Todas</option>
        ${pastas.map(p => `<option value="${p}" ${state.filters.documentos.pasta === p ? 'selected' : ''}>${p}</option>`).join('')}
      </select>
      <input id="docDataIni" type="date" value="${state.filters.documentos.dataIni}" />
      <input id="docDataFim" type="date" value="${state.filters.documentos.dataFim}" />
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Título</th>
            <th>Pasta</th>
            <th>Data</th>
            <th>Observação</th>
          </tr>
        </thead>
        <tbody>
          ${list.length === 0 ? '<tr><td colspan="4" class="empty-state">Nenhum documento encontrado.</td></tr>' : list.map(doc => `
            <tr>
              <td>${doc.titulo}</td>
              <td>${doc.pasta}</td>
              <td>${doc.data}</td>
              <td>${doc.observacao || '-'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  document.getElementById('docBusca')?.addEventListener('input', (event) => {
    state.filters.documentos.busca = event.target.value;
    renderDocumentos(state);
  });

  document.getElementById('docPasta')?.addEventListener('change', (event) => {
    state.filters.documentos.pasta = event.target.value;
    renderDocumentos(state);
  });

  document.getElementById('docDataIni')?.addEventListener('change', (event) => {
    state.filters.documentos.dataIni = event.target.value;
    renderDocumentos(state);
  });

  document.getElementById('docDataFim')?.addEventListener('change', (event) => {
    state.filters.documentos.dataFim = event.target.value;
    renderDocumentos(state);
  });
}
