import { DEFAULT_DATA } from './data/defaultData.js';
import { loadDb, saveDb } from './js/storage.js';
import { renderLogin } from './js/auth.js';
import { renderDashboard } from './js/modules/dashboard.js';
import { renderFinanceiro } from './js/modules/financeiro.js';
import { renderEstoque } from './js/modules/estoque.js';
import { renderDocumentos } from './js/modules/documentos.js';
import { renderMoradores } from './js/modules/moradores.js';
import { renderUsuarios } from './js/modules/usuarios.js';
import { renderRelatorios } from './js/modules/relatorios.js';

const state = {
  db: loadDb() || DEFAULT_DATA,
  user: null,
  activeTab: 'dashboard',
  filters: {
    financeiro: {
      busca: '',
      status: 'Todos',
      tipo: 'Todos'
    },
    estoque: {
      busca: '',
      categoria: 'Todas',
      status: 'Todos'
    },
    documentos: {
      busca: '',
      pasta: 'Todas',
      dataIni: '',
      dataFim: ''
    },
    moradores: {
      busca: '',
      bloco: 'Todos',
      tipo: 'Todos'
    },
    usuarios: {
      busca: '',
      perfil: 'Todos',
      status: 'Todos'
    }
  }
};

function persistSessionUser() {
  if (state.user) {
    sessionStorage.setItem('guardioes_user', JSON.stringify(state.user));
  } else {
    sessionStorage.removeItem('guardioes_user');
  }
}

function restoreSessionUser() {
  try {
    const raw = sessionStorage.getItem('guardioes_user');
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (parsed && parsed.usuario) {
      state.user = parsed;
    }
  } catch (error) {
    console.error('Erro ao restaurar sessão:', error);
  }
}

function renderCurrentModule() {
  const content = document.getElementById('content');
  if (!content) return;

  switch (state.activeTab) {
    case 'dashboard':
      renderDashboard(state);
      break;
    case 'financeiro':
      renderFinanceiro(state);
      break;
    case 'estoque':
      renderEstoque(state);
      break;
    case 'documentos':
      renderDocumentos(state);
      break;
    case 'moradores':
      renderMoradores(state);
      break;
    case 'usuarios':
      renderUsuarios(state);
      break;
    case 'relatorios':
      renderRelatorios(state);
      break;
    default:
      content.innerHTML = '<p>Módulo em desenvolvimento.</p>';
  }
}

function bindTabs() {
  document.querySelectorAll('[data-tab]').forEach(button => {
    button.addEventListener('click', () => {
      state.activeTab = button.dataset.tab;
      renderApp();
    });
  });
}

function bindLogin() {
  const form = document.getElementById('loginForm');
  if (!form) return;

  form.addEventListener('submit', (event) => {
    event.preventDefault();

    const userInput = document.getElementById('login_user').value.trim();
    const senhaInput = document.getElementById('login_pass').value;
    const userFound = state.db.usuarios.find(u =>
      (u.usuario === userInput || u.email === userInput) && u.senhaHash === senhaInput
    );

    if (!userFound) {
      alert('Credenciais incorretas!');
      return;
    }

    state.user = userFound;
    persistSessionUser();
    saveDb(state.db);
    renderApp();
  });
}

function renderApp() {
  const root = document.getElementById('app');
  if (!root) return;

  if (!state.user) {
    root.innerHTML = renderLogin();
    bindLogin();
    return;
  }

  root.innerHTML = `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark"><i class="fa-solid fa-shield-halved"></i></div>
          <div>
            <h1>Guardiões</h1>
            <small>Gestão Condominial</small>
          </div>
        </div>

        <nav class="nav-menu">
          <button class="nav-item ${state.activeTab === 'dashboard' ? 'active' : ''}" data-tab="dashboard">
            <i class="fa-solid fa-gauge-high"></i> Dashboard
          </button>
          <button class="nav-item ${state.activeTab === 'financeiro' ? 'active' : ''}" data-tab="financeiro">
            <i class="fa-solid fa-money-bill-wave"></i> Financeiro
          </button>
          <button class="nav-item ${state.activeTab === 'estoque' ? 'active' : ''}" data-tab="estoque">
            <i class="fa-solid fa-boxes-stacked"></i> Estoque
          </button>
          <button class="nav-item ${state.activeTab === 'documentos' ? 'active' : ''}" data-tab="documentos">
            <i class="fa-solid fa-folder-open"></i> Documentos
          </button>
          <button class="nav-item ${state.activeTab === 'moradores' ? 'active' : ''}" data-tab="moradores">
            <i class="fa-solid fa-user-tie"></i> Moradores
          </button>
          <button class="nav-item ${state.activeTab === 'usuarios' ? 'active' : ''}" data-tab="usuarios">
            <i class="fa-solid fa-users"></i> Usuários
          </button>
          <button class="nav-item ${state.activeTab === 'relatorios' ? 'active' : ''}" data-tab="relatorios">
            <i class="fa-solid fa-chart-column"></i> Relatórios
          </button>
        </nav>

        <div class="sidebar-user">
          <span>${state.user.nome}</span>
          <button id="logoutBtn" class="logout-btn">Sair</button>
        </div>
      </aside>

      <main class="main-panel">
        <div id="content"></div>
      </main>
    </div>
  `;

  bindTabs();
  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    state.user = null;
    persistSessionUser();
    renderApp();
  });
  renderCurrentModule();
}

restoreSessionUser();
renderApp();
