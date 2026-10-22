export function renderLogin() {
  return `
    <div class="login-screen">
      <div class="login-box">
        <div class="login-logo">
          <i class="fa-solid fa-shield-halved"></i>
        </div>
        <h2>Guardiões do Bravo</h2>
        <p>Acesso ao Sistema Condominial</p>

        <form id="loginForm" class="login-form">
          <label>Usuário / E-mail</label>
          <input id="login_user" type="text" value="admin" required />

          <label>Senha</label>
          <input id="login_pass" type="password" value="Admin@12345" required />

          <button type="submit">Entrar no Sistema</button>
        </form>
      </div>
    </div>
  `;
}
