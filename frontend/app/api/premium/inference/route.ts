import { NextRequest, NextResponse } from "next/server";

import { runPremiumInference, validatePremiumInput } from "../../premium/router";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const input = validatePremiumInput(body);
    const result = await runPremiumInference(input);

    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Premium inference failed",
      },
      { status: 400 },
    );
  }
}