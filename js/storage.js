const STORAGE_KEY = 'guardioes_bravo_db_v2';

export function loadDb() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed;
  } catch (error) {
    console.error('Erro ao carregar dados do storage:', error);
    return null;
  }
}

export function saveDb(db) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch (error) {
    alert('Aviso: armazenamento local cheio.');
  }
}
