export default function SobrePage() {
  return (
    <article className="page about-page">
      <header className="page-heading">
        <p className="eyebrow">Sobre a base</p>
        <h1>Dados e consulta</h1>
        <p className="page-lead">Entenda o que está disponível nesta aplicação.</p>
      </header>
      <div className="prose">
        <section><h2>Registros</h2><p>A base reúne servidores ativos e aposentados. Cada resposta pode conter identificador, CPF, nome, cargo, órgão, UF, tipo de vínculo e remuneração. Alguns campos podem não estar informados na fonte.</p></section>
        <section><h2>Como pesquisar</h2><p>A busca exata exige o nome completo. A busca aproximada aceita trechos e similaridade. Cargo e órgão também aceitam correspondência parcial; UF é um filtro exato.</p></section>
        <section><h2>Limites atuais</h2><p>A API retorna no máximo 100 registros por consulta e, neste momento, não oferece criação, edição, exclusão nem consulta individual por ID.</p></section>
      </div>
    </article>
  );
}
