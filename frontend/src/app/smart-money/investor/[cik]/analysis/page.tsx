import Link from "next/link";

export default async function InvestorAnalysisPage({
  params,
}: {
  params: Promise<{ cik: string }>;
}) {
  const { cik } = await params;
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-8 text-center dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="text-lg font-medium">Thesis analysis coming soon</h2>
      <p className="mt-2 text-sm text-zinc-500">
        AI-powered investor thesis analysis will be available in a future release.
      </p>
      <Link
        href={`/smart-money/investor/${cik}`}
        className="mt-4 inline-block text-sm text-zinc-600 hover:underline dark:text-zinc-400"
      >
        ← Back to profile
      </Link>
    </div>
  );
}
