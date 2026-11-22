import { notFound } from "next/navigation";
import SignupDesignPreview from "./SignupDesignPreview";

/** Review route: Vercel previews and local development only. */
export default function Page() {
  if (process.env.VERCEL_ENV !== "preview" && process.env.NODE_ENV !== "development") notFound();
  return <SignupDesignPreview />;
}
