export const DEFAULT_DATA = {
  usuarios: [
    {
      id: 'usr_admin',
      usuario: 'admin',
      nome: 'Administrador Principal',
      email: 'admin@guardioes.com',
      perfil: 'Admin',
      status: 'Ativo',
      primeiroAcesso: false,
      senhaHash: 'Admin@12345'
    }
  ],
  financeiro: [
    {
      id: 'fin_1',
      tipo: 'Receber',
      historico: 'Taxa Condominial Ordinária - Ap 101',
      valor: 2500.0,
      vencimento: '2026-10-15',
      competencia: '10/2026',
      status: 'Aberto',
      formaMonetariaId: 'fm_1'
    },
    {
      id: 'fin_2',
      tipo: 'Pagar',
      historico: 'Manutenção Elevador Otis',
      valor: 850.0,
      vencimento: '2026-10-20',
      competencia: '10/2026',
      status: 'Aberto',
      fornecedor: 'Otis Elevadores',
      formaMonetariaId: 'fm_1'
    }
  ],
  formas_monetarias: [
    {
      id: 'fm_1',
      nome: 'MOVIMENTO BANCARIO',
      contaId: 'cb_1',
      multaPct: 2.0,
      jurosDiaPct: 0.033,
      baixaAutomatica: true,
      status: 'Ativo'
    }
  ],
  contas_bancarias: [
    {
      id: 'cb_1',
      banco: 'CAIXA BARAO',
      agencia: '1234-5',
      conta: '98765-4',
      saldo: 45800.0
    }
  ],
  moradores: [
    {
      id: 'mor_1',
      bloco: 'A',
      apartamento: '101',
      nome: 'Carlos Eduardo',
      email: 'carlos@email.com',
      telefone: '(41) 99999-1111',
      tipo: 'Proprietário',
      taxaMudanca: 'N/A'
    }
  ],
  categorias: [
    { id: 'cat_1', nome: 'Atas de Assembleia', modulo: 'Documentos' },
    { id: 'cat_2', nome: 'Contratos', modulo: 'Documentos' },
    { id: 'cat_3', nome: 'Prestação de Contas', modulo: 'Documentos' },
    { id: 'cat_4', nome: 'Elétrica', modulo: 'Estoque' },
    { id: 'cat_5', nome: 'Piscina', modulo: 'Estoque' },
    { id: 'cat_6', nome: 'Geral', modulo: 'Geral' }
  ],
  estoque: [
    {
      id: 'est_1',
      item: 'Lâmpada LED 12W',
      categoria: 'Elétrica',
      qtd: 4,
      minimo: 10,
      maximo: 50,
      localizacao: 'Almoxarifado Central',
      proximaContagem: '2026-10-25',
      fotoBase64: ''
    },
    {
      id: 'est_2',
      item: 'Cloro Granulado 10kg',
      categoria: 'Piscina',
      qtd: 15,
      minimo: 5,
      maximo: 30,
      localizacao: 'DML Piscina',
      proximaContagem: '2026-11-01',
      fotoBase64: ''
    }
  ],
  documentos: [
    {
      id: 'doc_1',
      titulo: 'Ata da Assembleia 2026',
      pasta: 'Atas de Assembleia',
      data: '2026-03-10',
      observacao: 'Ata de eleição do síndico',
      arquivoBase64: ''
    }
  ],
  dre_config: [
    { id: 'A', codigo: 'REC_BRUTA', label: '(+) RECEITA OPERACIONAL BRUTA', tipo: 'direto', operacao: 'somar_receitas' },
    { id: 'B', codigo: 'INADIMP', label: '(-) INADIMPLÊNCIA / ABATIMENTOS', tipo: 'direto', operacao: 'somar_pendencias' },
    { id: 'C', codigo: 'REC_LIQ', label: '(=) RECEITA OPERACIONAL LÍQUIDA', tipo: 'formula', formula: 'A - B' },
    { id: 'D', codigo: 'DESP_OP', label: '(-) DESPESAS OPERACIONAIS & MANUTENÇÃO', tipo: 'direto', operacao: 'somar_despesas' },
    { id: 'E', codigo: 'RES_LIQ', label: '(=) RESULTADO OPERACIONAL (SUPERÁVIT/DEFICIT)', tipo: 'formula', formula: 'C - D' }
  ],
  logs: []
};
