import { Story } from '@/types';
import { Button } from '@/components/ui/Button';

interface StoryDetailProps {
  story: Story;
  onBack?: () => void;
}

export function StoryDetail({ story, onBack }: StoryDetailProps) {
  return (
    <div className="max-w-4xl mx-auto">
      {onBack && (
        <Button variant="ghost" onClick={onBack} className="mb-4">
          ← Back to results
        </Button>
      )}
      
      <article className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            {story.title}
          </h1>
          
          <div className="flex items-center justify-between text-sm text-gray-600 mb-4">
            <div className="flex items-center space-x-4">
              <span>By <span className="font-medium">{story.author}</span></span>
              <span>{story.views} views</span>
              {story.rating && (
                <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                  ⭐ {story.rating}
                </span>
              )}
            </div>
            <time dateTime={story.createdAt}>
              {new Date(story.createdAt).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              })}
            </time>
          </div>
          
          {story.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {story.tags.map(tag => (
                <span 
                  key={tag}
                  className="bg-gray-100 text-gray-700 text-sm px-3 py-1 rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </header>
        
        <div className="prose prose-lg max-w-none">
          {story.content.split('\n').map((paragraph, index) => (
            <p key={index} className="mb-4 text-gray-800 leading-relaxed">
              {paragraph}
            </p>
          ))}
        </div>
      </article>
    </div>
  );
}