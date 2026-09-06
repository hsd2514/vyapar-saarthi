// A to-scale SVG break-even chart: total cost vs. revenue lines crossing
// at the break-even point. Every mark is placed by the same numbers shown
// in the stat rows above it - nothing here is decorative.

export default function BreakEvenChart({ be }) {
  if (!be.isViable || !be.breakEvenUnits || be.breakEvenUnits <= 0) {
    return (
      <div className="mt-4 rounded-xl border border-line bg-paper/60 p-4 text-sm text-ink-faint text-center py-10">
        Enter a price above your variable cost to see the break-even chart.
      </div>
    );
  }

  const w = 560;
  const h = 240;
  const pad = { top: 16, right: 20, bottom: 34, left: 64 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  const maxUnits = be.breakEvenUnits * 2;
  const maxRevenue = maxUnits * be.pricePerUnit;
  const maxCost = be.fixedCosts + maxUnits * be.variableCostPerUnit;
  const maxY = Math.max(maxRevenue, maxCost) * 1.05;

  const x = (units) => pad.left + (units / maxUnits) * plotW;
  const y = (rupees) => pad.top + plotH - (rupees / maxY) * plotH;

  const revenueLine = `M ${x(0)} ${y(0)} L ${x(maxUnits)} ${y(maxUnits * be.pricePerUnit)}`;
  const costLine = `M ${x(0)} ${y(be.fixedCosts)} L ${x(maxUnits)} ${y(maxCost)}`;
  const fixedLine = `M ${x(0)} ${y(be.fixedCosts)} L ${x(maxUnits)} ${y(be.fixedCosts)}`;

  const bx = x(be.breakEvenUnits);
  const by = y(be.breakEvenRevenue);

  const yTicks = [0, maxY * 0.25, maxY * 0.5, maxY * 0.75, maxY].map((v) => Math.round(v));
  const xTicks = [0, be.breakEvenUnits, maxUnits];

  return (
    <div className="mt-4 rounded-xl border border-line bg-paper/60 p-4">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto" role="img" aria-label="Break-even chart">
        {yTicks.map((v, i) => (
          <g key={i}>
            <line x1={pad.left} x2={w - pad.right} y1={y(v)} y2={y(v)} stroke="#e2e6eb" strokeWidth="1" />
            <text x={pad.left - 8} y={y(v)} textAnchor="end" dominantBaseline="middle" fontSize="10" fontFamily="JetBrains Mono, monospace" fill="#8891a0">
              Rs {Math.round(v).toLocaleString("en-IN")}
            </text>
          </g>
        ))}

        <path d={fixedLine} stroke="#c7cfd8" strokeWidth="1.5" strokeDasharray="3 4" fill="none" />
        <path d={costLine} stroke="#d6402a" strokeWidth="2.5" fill="none" />
        <path d={revenueLine} stroke="#0fa968" strokeWidth="2.5" fill="none" />

        <line x1={bx} x2={bx} y1={by} y2={pad.top + plotH} stroke="#c2760a" strokeWidth="1.5" strokeDasharray="2 3" />
        <line x1={pad.left} x2={bx} y1={by} y2={by} stroke="#c2760a" strokeWidth="1.5" strokeDasharray="2 3" />
        <circle cx={bx} cy={by} r="5" fill="#c2760a" stroke="#ffffff" strokeWidth="2" />

        <line x1={pad.left} x2={w - pad.right} y1={pad.top + plotH} y2={pad.top + plotH} stroke="#c7cfd8" strokeWidth="1" />
        {xTicks.map((v, i) => (
          <text key={i} x={x(v)} y={h - 10} textAnchor={i === 0 ? "start" : i === xTicks.length - 1 ? "end" : "middle"} fontSize="10" fontFamily="JetBrains Mono, monospace" fill="#8891a0">
            {Math.round(v).toLocaleString("en-IN")} u
          </text>
        ))}

        <text x={bx} y={by - 12} textAnchor="middle" fontSize="10.5" fontWeight="600" fontFamily="Public Sans, sans-serif" fill="#c2760a">
          Break-even
        </text>
      </svg>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-2 text-xs text-ink-soft">
        <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-3.5 bg-pine inline-block" /> Revenue</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-3.5 bg-clay inline-block" /> Total cost</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-3.5 border-t border-dashed border-line-strong inline-block" /> Fixed cost</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-gold inline-block" /> Break-even point</span>
      </div>
    </div>
  );
}
