import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api } from '../api'
import { openExternalLink } from '../telegram'
import type { BreakdownData, HistogramData, ScatterData } from '../types'

const COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#898781']

// Mirrors bot/charts.py's _histogram bin-count choice, so the two only ever
// differ in rendering (static PNG vs. interactive), never in what a "bin" is.
function binCountFor(n: number): number {
  return Math.min(20, Math.max(5, Math.floor(n / 3)))
}

function histogramBins(values: number[]): { bin: string; count: number }[] {
  if (values.length === 0) return []
  const binCount = binCountFor(values.length)
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (min === max) return [{ bin: Math.round(min).toLocaleString(), count: values.length }]
  const width = (max - min) / binCount
  const buckets = new Array(binCount).fill(0) as number[]
  for (const value of values) {
    const index = Math.min(binCount - 1, Math.floor((value - min) / width))
    buckets[index] += 1
  }
  return buckets.map((count, i) => ({ bin: Math.round(min + i * width).toLocaleString(), count }))
}

function Histogram({ data }: { data: HistogramData }) {
  const bins = histogramBins(data.values)
  if (bins.length === 0) return <p className="listing-card__meta">No data yet.</p>
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={bins}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="bin" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="count" fill={COLORS[0]} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function ScatterPlot({ data }: { data: ScatterData }) {
  if (data.points.length === 0) return <p className="listing-card__meta">No data yet.</p>
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" dataKey="area" name="Area (m²)" tick={{ fontSize: 11 }} />
        <YAxis type="number" dataKey="price" name="Total price" tick={{ fontSize: 11 }} />
        <Tooltip cursor={{ strokeDasharray: '3 3' }} />
        <Scatter
          data={data.points}
          fill={COLORS[0]}
          cursor="pointer"
          onClick={(point) => {
            const url = (point.payload as { url?: string } | undefined)?.url
            if (url) openExternalLink(url)
          }}
        />
      </ScatterChart>
    </ResponsiveContainer>
  )
}

function Breakdown({ data }: { data: BreakdownData }) {
  if (data.counts.length === 0) return <p className="listing-card__meta">No data yet.</p>
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie data={data.counts} dataKey="value" nameKey="label" outerRadius={90} label>
          {data.counts.map((entry, index) => (
            <Cell key={entry.label} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Legend />
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  )
}

export default function Charts() {
  const options = useQuery({ queryKey: ['charts'], queryFn: api.charts })
  const [selected, setSelected] = useState<string | null>(null)
  const activeKey = selected ?? options.data?.[0]?.key ?? null

  const chart = useQuery({
    queryKey: ['charts', activeKey],
    queryFn: () => api.chartData(activeKey as string),
    enabled: Boolean(activeKey),
  })

  return (
    <div className="stack">
      <h1 className="screen-title">Charts</h1>
      <div className="chart-tabs">
        {(options.data ?? []).map((option) => (
          <button
            key={option.key}
            type="button"
            className={option.key === activeKey ? 'active' : ''}
            onClick={() => setSelected(option.key)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {chart.isLoading && <p>Loading…</p>}
      {chart.data?.kind === 'histogram' && <Histogram data={chart.data.data as HistogramData} />}
      {chart.data?.kind === 'scatter' && <ScatterPlot data={chart.data.data as ScatterData} />}
      {chart.data?.kind === 'pie' && <Breakdown data={chart.data.data as BreakdownData} />}
    </div>
  )
}
