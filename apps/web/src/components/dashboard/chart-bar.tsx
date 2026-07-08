import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Title,
  Tooltip,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(BarElement, CategoryScale, LinearScale, Title, Tooltip, Legend)

interface ChartBarProps {
  labels: string[]
  datasets: {
    label: string
    data: number[]
    backgroundColor?: string | string[]
    borderColor?: string | string[]
    borderWidth?: number
  }[]
  title?: string
  height?: number
  horizontal?: boolean
}

export function ChartBar({
  labels,
  datasets,
  title,
  height = 220,
  horizontal = false,
}: ChartBarProps) {
  return (
    <div style={{ height }}>
      <Bar
        data={{ labels, datasets }}
        options={{
          indexAxis: horizontal ? 'y' : 'x',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: datasets.length > 1 },
            title: { display: !!title, text: title },
          },
          scales: {
            x: { grid: { display: false } },
            y: { grid: { color: '#f0f0f0' }, beginAtZero: true },
          },
        }}
      />
    </div>
  )
}
