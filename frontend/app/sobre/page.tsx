export default function SobrePage() {
  return (
    <article className="page about-page">
      <header className="page-heading">
        <p className="eyebrow">Sobre a base</p>
        <h1>Dados e consulta</h1>
        <p className="page-lead">Entenda o que está disponível nesta aplicação.</p>
      </header>
      <div className="prose">
        <section><h2>Registros</h2><p>A consulta reúne as bases de carreiras de agosto de 2026 e de aposentados de agosto de 2025. Abra um registro para ver os campos da fonte, como código da carreira, matrícula ou portaria de aposentadoria.</p></section>
        <section><h2>Como pesquisar</h2><p>A busca exata usa o nome completo do servidor. A aproximada aceita trechos do nome. Você também pode pesquisar o órgão pelo nome ou pela sigla, como FURG. O filtro de UF usa o estado da unidade pagadora, informado na base de carreiras.</p></section>
        <section><h2>Limites atuais</h2><p>A API oferece consultas de leitura, com até 100 registros por página.</p></section>
      </div>
    </article>
  );
}
