import { notFound } from "next/navigation";
import OperationsPreview from "./OperationsPreview";

/** Visual review only: never publicly available on the production deployment. */
export default function Page() {
  if (process.env.VERCEL_ENV !== "preview" && process.env.NODE_ENV !== "development") notFound();
  return <OperationsPreview />;
}