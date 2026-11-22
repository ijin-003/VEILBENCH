import FounderSubmissionForm from "./FounderSubmissionForm";

type FounderRouteParams = {
  sessionId: string;
  partyId: string;
};

export default async function FounderSubmissionPage({
  params,
}: {
  params: Promise<FounderRouteParams>;
}) {
  const { sessionId, partyId } = await params;

  return <FounderSubmissionForm sessionId={sessionId} partyId={partyId} />;
}
