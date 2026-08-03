import { NextResponse } from "next/server";

import { getVectorStore } from "@/lib/server/documents/stores/local-json";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

export async function GET(request: Request) {
  const userId = getUserId(request);
  const store = getVectorStore();
  const documents = await store.listDocuments(userId);

  return NextResponse.json({
    ok: true,
    documents,
  });
}