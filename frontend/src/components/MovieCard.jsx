import { Link } from 'react-router-dom'
import { Bookmark, Star } from 'lucide-react'

export default function MovieCard({ movie, onToggleWatch, saved }) {
  return (
    <div className="group relative">
      <Link to={`/movies/${movie.id}`} className="block">
        <div className="relative aspect-[2/3] overflow-hidden rounded-xl border border-edge bg-panel shadow-lg shadow-black/30 transition duration-300 group-hover:-translate-y-1 group-hover:border-slate-500">
          {movie.poster_url && <img src={movie.poster_url} alt={`${movie.title} poster`} loading="lazy" className="h-full w-full object-cover transition duration-500 group-hover:scale-105" />}
          <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-black/90 to-transparent px-3 pb-2 pt-8 text-xs">
            <span className="rounded bg-black/60 px-1.5 py-0.5 font-medium text-slate-200">{movie.certificate}</span>
            <span className="flex items-center gap-1 font-semibold text-amber-400"><Star size={12} fill="currentColor" />{movie.rating_count ? movie.avg_rating : 'New'}</span>
          </div>
        </div>
        <div className="mt-2.5 space-y-0.5 px-0.5">
          <h3 className="line-clamp-1 text-sm font-semibold text-slate-100">{movie.title}</h3>
          <p className="line-clamp-1 text-xs text-slate-400">{movie.genres.join(', ')} &middot; {movie.language} &middot; {movie.duration_min} min</p>
        </div>
      </Link>
      {onToggleWatch && (
        <button onClick={() => onToggleWatch(movie.id)} aria-label={saved ? 'Remove from watchlist' : 'Add to watchlist'} aria-pressed={!!saved}
          className="absolute right-2 top-2 rounded-md bg-black/60 p-1.5 backdrop-blur hover:bg-black">
          <Bookmark size={16} className={saved ? 'fill-white text-white' : 'text-white'} />
        </button>
      )}
    </div>
  )
}
