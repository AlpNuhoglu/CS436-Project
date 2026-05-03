interface Props {
  value: number
  max?: number
  size?: 'sm' | 'md' | 'lg'
  interactive?: boolean
  onChange?: (v: number) => void
}

const sizes = { sm: 'text-sm', md: 'text-lg', lg: 'text-2xl' }

export default function StarRating({ value, max = 5, size = 'md', interactive, onChange }: Props) {
  return (
    <div className={`flex gap-0.5 ${sizes[size]}`}>
      {Array.from({ length: max }).map((_, i) => (
        <span
          key={i}
          onClick={() => interactive && onChange?.(i + 1)}
          className={`${interactive ? 'cursor-pointer hover:scale-110 transition-transform' : ''}
            ${i < Math.round(value) ? 'text-amber-400' : 'text-gray-300'}`}
        >
          ★
        </span>
      ))}
    </div>
  )
}
