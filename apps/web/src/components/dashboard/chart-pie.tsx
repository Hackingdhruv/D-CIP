import {
  ArcElement,
  Chart as ChartJS,
  Legend,
  Tooltip,
} from 'chart.js'
import { Doughnut } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend)

const PALETTE = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#06b6d4', '#f97316', '#ec4899',
  '#14b8a6', '#6366f1',
]

interface ChartPieProps {
  labels: string[]
  data: number[]
  title?: string
  height?: number
  colors?: string[]
}

export function ChartPie({
  labels,
  data,
  title,
  height = 220,
  colors = PALETTE,
}: ChartPieProps) {
  return (
    <div style={{ height }}>
      <Doughnut
        data={{
          labels,
          datasets: [
            {
              data,
              backgroundColor: colors.slice(0, data.length),
              borderWidth: 2,
              borderColor: '#fff',
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { font: { size: 11 } } },
            title: { display: !!title, text: title },
          },
          cutout: '60%',
        }}
      />
    </div>
  )
}
