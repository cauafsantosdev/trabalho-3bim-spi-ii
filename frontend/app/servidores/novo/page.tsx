import { ServidorForm } from "@/components/ServidorForm";

export default function NovoServidorPage() {
  return (
    <div className="page form-page">
      <header className="page-heading compact">
        <p className="breadcrumbs"><span>Registros</span><i>/</i><strong>Novo</strong></p>
        <h1>Novo registro</h1>
        <p className="page-lead">Preencha os dados de um servidor.</p>
      </header>
      <div className="form-layout">
        <ServidorForm />
        <aside className="editorial-note">
          <span className="accent-rule" />
          <h2>Cadastro ainda não disponível.</h2>
          <p>A interface está pronta, mas a API atual oferece apenas consulta. O formulário não simula gravações.</p>
        </aside>
      </div>
    </div>
  );
}
