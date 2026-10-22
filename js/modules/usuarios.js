export function renderUsuarios(state) {
  const container = document.getElementById('content');

  const list = state.db.usuarios.filter(item => {
    const busca = state.filters.usuarios.busca.toLowerCase();
    const matchesBusca =
      !busca ||
      (item.nome || '').toLowerCase().includes(busca) ||
      (item.usuario || '').toLowerCase().includes(busca) ||
      (item.email || '').toLowerCase().includes(busca);

    const matchesPerfil =
      state.filters.usuarios.perfil === 'Todos' || item.perfil === state.filters.usuarios.perfil;

    const matchesStatus =
      state.filters.usuarios.status === 'Todos' || item.status === state.filters.usuarios.status;

    return matchesBusca && matchesPerfil && matchesStatus;
  });

  container.innerHTML = `
    <section class="section-header">
      <div>
        <h2>Gestão de usuários</h2>
        <p>Perfis, status e administração de acessos</p>
      </div>
    </section>

    <div class="toolbar">
      <input id="usuarioBusca" type="text" placeholder="Buscar usuário..." value="${state.filters.usuarios.busca}" />
      <select id="usuarioPerfil">
        <option value="Todos" ${state.filters.usuarios.perfil === 'Todos' ? 'selected' : ''}>Todos</option>
        <option value="Admin" ${state.filters.usuarios.perfil === 'Admin' ? 'selected' : ''}>Admin</option>
        <option value="Operador" ${state.filters.usuarios.perfil === 'Operador' ? 'selected' : ''}>Operador</option>
      </select>
      <select id="usuarioStatus">
        <option value="Todos" ${state.filters.usuarios.status === 'Todos' ? 'selected' : ''}>Todos</option>
        <option value="Ativo" ${state.filters.usuarios.status === 'Ativo' ? 'selected' : ''}>Ativo</option>
        <option value="Inativo" ${state.filters.usuarios.status === 'Inativo' ? 'selected' : ''}>Inativo</option>
      </select>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Usuário</th>
            <th>Nome</th>
            <th>Email</th>
            <th>Perfil</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${list.length === 0 ? '<tr><td colspan="5" class="empty-state">Nenhum usuário encontrado.</td></tr>' : list.map(item => `
            <tr>
              <td>${item.usuario}</td>
              <td>${item.nome}</td>
              <td>${item.email}</td>
              <td>${item.perfil}</td>
              <td>${item.status}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  document.getElementById('usuarioBusca')?.addEventListener('input', (event) => {
    state.filters.usuarios.busca = event.target.value;
    renderUsuarios(state);
  });

  document.getElementById('usuarioPerfil')?.addEventListener('change', (event) => {
    state.filters.usuarios.perfil = event.target.value;
    renderUsuarios(state);
  });

  document.getElementById('usuarioStatus')?.addEventListener('change', (event) => {
    state.filters.usuarios.status = event.target.value;
    renderUsuarios(state);
  });
}
