"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  ChartDataRow,
  ChartSpec,
} from "@/types/chart";


type ChartRendererProps = {
  spec: ChartSpec;

  height?: number;

  showMetadata?: boolean;
};


const SERIES_COLORS = [
  "#22d3ee",
  "#fbbf24",
  "#a78bfa",
  "#34d399",
  "#fb7185",
  "#60a5fa",
  "#f97316",
  "#2dd4bf",
];


function seriesColor(
  index: number,
) {
  return SERIES_COLORS[
    index %
      SERIES_COLORS.length
  ];
}


function formatCompactNumber(
  value: number,
) {
  const absolute =
    Math.abs(value);

  if (
    absolute >=
    1_000_000_000
  ) {
    return `${(
      value /
      1_000_000_000
    ).toFixed(1)}B`;
  }

  if (
    absolute >=
    1_000_000
  ) {
    return `${(
      value / 1_000_000
    ).toFixed(1)}M`;
  }

  if (
    absolute >=
    1_000
  ) {
    return `${(
      value / 1_000
    ).toFixed(1)}K`;
  }

  return new Intl.NumberFormat(
    undefined,
    {
      maximumFractionDigits: 2,
    },
  ).format(value);
}


function formatAxisValue(
  value: unknown,
) {
  if (
    typeof value ===
    "number"
  ) {
    return formatCompactNumber(
      value,
    );
  }

  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  return String(value);
}


function coverageLabel(
  coverage: number,
) {
  return `${Math.round(
    coverage * 100,
  )}%`;
}


export function ChartRenderer({
  spec,
  height = 380,
  showMetadata = true,
}: ChartRendererProps) {
  if (!spec.data.length) {
    return (
      <ChartError
        message="The chart specification does not contain any data points."
      />
    );
  }

  const chart = renderChart(
    spec,
    height,
  );

  return (
    <section className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
      <header className="border-b border-white/10 px-4 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              {
                spec.chart_type
              }{" "}
              visualization
            </p>

            <h3 className="mt-1 text-base font-semibold text-white">
              {spec.title}
            </h3>

            {spec.explanation ? (
              <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">
                {
                  spec.explanation
                }
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[10px] font-semibold text-cyan-100">
              {
                spec.chart_row_count
              }{" "}
              points
            </span>

            <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-100">
              {
                coverageLabel(
                  spec.source_coverage,
                )
              }{" "}
              source coverage
            </span>

            {spec.sampled ? (
              <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-2.5 py-1 text-[10px] font-semibold text-amber-100">
                sampled
              </span>
            ) : null}
          </div>
        </div>
      </header>

      <div className="p-3 sm:p-4">
        {chart}
      </div>

      {showMetadata ? (
        <ChartMetadata
          spec={spec}
        />
      ) : null}
    </section>
  );
}


function renderChart(
  spec: ChartSpec,
  height: number,
) {
  switch (
    spec.chart_type
  ) {
    case "line":
      return (
        <LineChartView
          spec={spec}
          height={height}
        />
      );

    case "bar":
      return (
        <BarChartView
          spec={spec}
          height={height}
        />
      );

    case "area":
      return (
        <AreaChartView
          spec={spec}
          height={height}
        />
      );

    case "scatter":
      return (
        <ScatterChartView
          spec={spec}
          height={height}
        />
      );

    case "table":
      return (
        <TableChartView
          spec={spec}
        />
      );

    default:
      return (
        <ChartError
          message="Unsupported chart type."
        />
      );
  }
}


function LineChartView({
  spec,
  height,
}: {
  spec: ChartSpec;
  height: number;
}) {
  if (
    !spec.x ||
    !spec.series.length
  ) {
    return (
      <ChartError
        message="Line chart requires an x-axis and at least one series."
      />
    );
  }

  return (
    <div
      style={{
        height,
      }}
      className="w-full"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
      >
        <LineChart
          data={spec.data}
          margin={{
            top: 16,
            right: 20,
            bottom: 12,
            left: 4,
          }}
        >
          <CartesianGrid
            stroke="rgba(148,163,184,0.12)"
            vertical={false}
          />

          <XAxis
            dataKey={spec.x}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={{
              stroke:
                "rgba(148,163,184,0.25)",
            }}
            tickLine={false}
            minTickGap={24}
          />

          <YAxis
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={
              formatAxisValue
            }
          />

          <Tooltip />

          <Legend />

          {spec.series.map(
            (
              seriesName,
              index,
            ) => (
              <Line
                key={
                  seriesName
                }
                type="monotone"
                dataKey={
                  seriesName
                }
                name={
                  seriesName
                }
                stroke={seriesColor(
                  index,
                )}
                strokeWidth={2}
                dot={false}
                activeDot={{
                  r: 4,
                }}
                connectNulls={
                  false
                }
              />
            ),
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}


function BarChartView({
  spec,
  height,
}: {
  spec: ChartSpec;
  height: number;
}) {
  if (
    !spec.x ||
    !spec.series.length
  ) {
    return (
      <ChartError
        message="Bar chart requires an x-axis and at least one series."
      />
    );
  }

  return (
    <div
      style={{
        height,
      }}
      className="w-full"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
      >
        <BarChart
          data={spec.data}
          margin={{
            top: 16,
            right: 20,
            bottom: 12,
            left: 4,
          }}
        >
          <CartesianGrid
            stroke="rgba(148,163,184,0.12)"
            vertical={false}
          />

          <XAxis
            dataKey={spec.x}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={{
              stroke:
                "rgba(148,163,184,0.25)",
            }}
            tickLine={false}
            minTickGap={20}
          />

          <YAxis
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={
              formatAxisValue
            }
          />

          <Tooltip />

          <Legend />

          {spec.series.map(
            (
              seriesName,
              index,
            ) => (
              <Bar
                key={
                  seriesName
                }
                dataKey={
                  seriesName
                }
                name={
                  seriesName
                }
                fill={seriesColor(
                  index,
                )}
                radius={[
                  4,
                  4,
                  0,
                  0,
                ]}
              />
            ),
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}


function AreaChartView({
  spec,
  height,
}: {
  spec: ChartSpec;
  height: number;
}) {
  if (
    !spec.x ||
    !spec.series.length
  ) {
    return (
      <ChartError
        message="Area chart requires an x-axis and at least one series."
      />
    );
  }

  return (
    <div
      style={{
        height,
      }}
      className="w-full"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
      >
        <AreaChart
          data={spec.data}
          margin={{
            top: 16,
            right: 20,
            bottom: 12,
            left: 4,
          }}
        >
          <CartesianGrid
            stroke="rgba(148,163,184,0.12)"
            vertical={false}
          />

          <XAxis
            dataKey={spec.x}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={{
              stroke:
                "rgba(148,163,184,0.25)",
            }}
            tickLine={false}
            minTickGap={24}
          />

          <YAxis
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={
              formatAxisValue
            }
          />

          <Tooltip />

          <Legend />

          {spec.series.map(
            (
              seriesName,
              index,
            ) => (
              <Area
                key={
                  seriesName
                }
                type="monotone"
                dataKey={
                  seriesName
                }
                name={
                  seriesName
                }
                stroke={seriesColor(
                  index,
                )}
                fill={seriesColor(
                  index,
                )}
                fillOpacity={
                  0.16
                }
                strokeWidth={2}
                connectNulls={
                  false
                }
              />
            ),
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}


function ScatterChartView({
  spec,
  height,
}: {
  spec: ChartSpec;
  height: number;
}) {
  const ySeries =
    spec.series[0];

  if (
    !spec.x ||
    !ySeries
  ) {
    return (
      <ChartError
        message="Scatter chart requires numeric x and y fields."
      />
    );
  }

  return (
    <div
      style={{
        height,
      }}
      className="w-full"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
      >
        <ScatterChart
          margin={{
            top: 16,
            right: 20,
            bottom: 20,
            left: 8,
          }}
        >
          <CartesianGrid
            stroke="rgba(148,163,184,0.12)"
          />

          <XAxis
            type="number"
            dataKey={spec.x}
            name={spec.x}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={{
              stroke:
                "rgba(148,163,184,0.25)",
            }}
            tickLine={false}
            tickFormatter={
              formatAxisValue
            }
          />

          <YAxis
            type="number"
            dataKey={ySeries}
            name={ySeries}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={
              formatAxisValue
            }
          />

          <Tooltip />

          <Legend />

          <Scatter
            name={ySeries}
            data={spec.data}
            fill={seriesColor(
              0,
            )}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}


function TableChartView({
  spec,
}: {
  spec: ChartSpec;
}) {
  const columns =
    getTableColumns(
      spec,
    );

  if (!columns.length) {
    return (
      <ChartError
        message="No table columns were returned."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="min-w-full border-collapse text-left text-xs">
        <thead className="bg-white/5">
          <tr>
            {columns.map(
              (column) => (
                <th
                  key={
                    column
                  }
                  className="whitespace-nowrap border-b border-white/10 px-4 py-3 font-semibold text-slate-300"
                >
                  {column}
                </th>
              ),
            )}
          </tr>
        </thead>

        <tbody>
          {spec.data.map(
            (
              row,
              rowIndex,
            ) => (
              <tr
                key={
                  rowIndex
                }
                className="border-b border-white/5 last:border-b-0"
              >
                {columns.map(
                  (
                    column,
                  ) => (
                    <td
                      key={
                        column
                      }
                      className="whitespace-nowrap px-4 py-3 text-slate-300"
                    >
                      {formatTableValue(
                        row[
                          column
                        ],
                      )}
                    </td>
                  ),
                )}
              </tr>
            ),
          )}
        </tbody>
      </table>
    </div>
  );
}


function getTableColumns(
  spec: ChartSpec,
) {
  const columns: string[] =
    [];

  if (spec.x) {
    columns.push(
      spec.x,
    );
  }

  for (
    const seriesName
    of spec.series
  ) {
    if (
      !columns.includes(
        seriesName,
      )
    ) {
      columns.push(
        seriesName,
      );
    }
  }

  if (
    !columns.length &&
    spec.data.length
  ) {
    return Object.keys(
      spec.data[0],
    );
  }

  return columns;
}


function formatTableValue(
  value:
    | ChartDataRow[string]
    | undefined,
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  if (
    typeof value ===
    "number"
  ) {
    return new Intl.NumberFormat(
      undefined,
      {
        maximumFractionDigits: 4,
      },
    ).format(value);
  }

  return String(value);
}


function ChartMetadata({
  spec,
}: {
  spec: ChartSpec;
}) {
  return (
    <footer className="border-t border-white/10 bg-white/[0.02] px-4 py-3">
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-slate-500">
        <span>
          Dataset:{" "}
          <span className="text-slate-300">
            {
              spec.file_name
            }
          </span>
        </span>

        <span>
          Source rows:{" "}
          <span className="text-slate-300">
            {
              spec.source_row_count
            }
          </span>
        </span>

        <span>
          Chart rows:{" "}
          <span className="text-slate-300">
            {
              spec.chart_row_count
            }
          </span>
        </span>

        {spec.x ? (
          <span>
            X:{" "}
            <span className="text-slate-300">
              {spec.x}
            </span>
          </span>
        ) : null}
      </div>

      {spec.warnings.length ? (
        <div className="mt-3 space-y-1.5">
          {spec.warnings.map(
            (
              warning,
              index,
            ) => (
              <p
                key={
                  index
                }
                className="rounded-lg border border-amber-300/15 bg-amber-300/5 px-3 py-2 text-xs text-amber-100"
              >
                {warning}
              </p>
            ),
          )}
        </div>
      ) : null}
    </footer>
  );
}


function ChartError({
  message,
}: {
  message: string;
}) {
  return (
    <div className="rounded-xl border border-rose-300/20 bg-rose-300/5 px-4 py-6 text-center">
      <p className="text-sm font-medium text-rose-100">
        Unable to render chart
      </p>

      <p className="mt-1 text-xs text-rose-200/70">
        {message}
      </p>
    </div>
  );
}