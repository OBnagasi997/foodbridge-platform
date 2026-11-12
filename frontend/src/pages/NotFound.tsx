import { ButtonLink, EmptyState } from "../components/ui";

export default function NotFound() {
  return (
    <EmptyState title="Cette page n'existe pas" action={<ButtonLink to="/">Revenir à l'accueil</ButtonLink>}>
      Le lien est peut-être incomplet ou la page a été déplacée.
    </EmptyState>
  );
}
