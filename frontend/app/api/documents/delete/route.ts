import { NextResponse } from "next/server";

import { getVectorStore } from "@/lib/server/documents/stores/local-json";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type DeleteBody = {
  documentId?: string;
};

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

export async function DELETE(request: Request) {
  const userId = getUserId(request);

  try {
    const body = (await request.json()) as DeleteBody;
    const documentId = body.documentId;

    if (!documentId) {
      return NextResponse.json(
        {
          ok: false,
          error: "documentId is required.",
        },
        { status: 400 },
      );
    }

    const store = getVectorStore();
    await store.deleteDocument(userId, documentId);

    return NextResponse.json({
      ok: true,
      documentId,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Document deletion failed.";

    return NextResponse.json(
      {
        ok: false,
        error: message,
      },
      { status: 500 },
    );
  }
}