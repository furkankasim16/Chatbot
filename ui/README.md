# Quiz Chatbot Widget

Modern, clean quiz chatbot web widget built with Next.js, React, and TypeScript. Integrates with a FastAPI backend for database-powered questions.

## Features

- **Three Quiz Modes**
  - Quick Quiz: 5 questions to test knowledge
  - Daily Question: One question per day (24-hour cooldown)
  - Scenario Task: Multi-step real-world scenarios

- **Four Question Types**
  - Multiple Choice (MCQ)
  - True/False
  - Short Answer
  - Multi-step Scenarios

- **Backend Integration**
  - **Fast SQLite database queries** - Questions loaded from pre-stored database
  - RAG-powered document search using ChromaDB
  - Optional Ollama/OpenRouter for new question generation
  - Document indexing and search

- **Modern UI/UX**
  - Dark mode by default with theme toggle
  - Responsive design (mobile-friendly)
  - Progress tracking and scoring
  - Source citations with document references
  - Smooth animations and transitions

## Setup

### Prerequisites

- Node.js 18+ 
- Python 3.9+ (for backend)
- SQLite database with pre-stored questions (`data/questions/questions.db`)

### Frontend Setup

1. Install dependencies:
\`\`\`bash
npm install
\`\`\`

2. Configure environment variables in Vercel Project Settings (gear icon, top right):
\`\`\`
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK_DATA=false
\`\`\`

3. Run the development server:
\`\`\`bash
npm run dev
\`\`\`

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Backend Setup

Your backend should have the following endpoints:

- `GET /health` - Health check
- `GET /topics` - Get available topics from database
- `GET /questions/random?topic={topic}&level={level}` - **Get random question from SQLite database** (FAST)
- `POST /quiz?topic={topic}&level={level}&n={n}` - Generate new quiz with Ollama (SLOW - optional)
- `POST /questions/generate` - Generate new question with Ollama (optional)
- `GET /questions/all` - List all questions from database

#### How It Works

**Fast Mode (Default)**: Widget calls `/questions/random` multiple times to fetch questions from your SQLite database. This is instant and doesn't require Ollama.

**Generation Mode (Optional)**: If you want to generate new questions, use the `/quiz` or `/questions/generate` endpoints which use Ollama.

#### CORS Configuration

Make sure your FastAPI backend has CORS enabled. Add this to your main FastAPI file:

\`\`\`python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. In production, use specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
\`\`\`

## Testing Without Backend

You can test the UI without running the backend by enabling mock mode:

1. Set in Vercel Project Settings:
\`\`\`
NEXT_PUBLIC_USE_MOCK_DATA=true
\`\`\`

2. Refresh the page

This will use sample questions instead of calling the backend API.

## Troubleshooting

### "Failed to fetch" Error

If you see this error:

1. **Check backend is running**: 
   \`\`\`bash
   python health-vl6Q6.py
   # Backend should start on http://localhost:8000
   \`\`\`

2. **Verify database has questions**: 
   - Check that `data/questions/questions.db` exists
   - Make sure it has questions in it

3. **Check API URL**: Verify `NEXT_PUBLIC_API_URL` in Project Settings matches your backend URL

4. **CORS issues**: Ensure CORS is properly configured in your FastAPI backend (see above)

5. **Test backend directly**: Open `http://localhost:8000/health` in browser - should return `{"status":"ok"}`

6. **Use mock mode**: Set `NEXT_PUBLIC_USE_MOCK_DATA=true` to test UI without backend

### Daily Question Not Resetting

The daily question cooldown is stored in browser localStorage. To reset it manually:
1. Open browser DevTools → Console
2. Run: `localStorage.removeItem('lastDailyQuizCompletion')`

### Questions Loading Slowly

If questions are loading slowly, make sure:
- You're using the database mode (default) not generation mode
- Your SQLite database has questions pre-stored
- Backend is running locally (not on a slow server)

## Project Structure

\`\`\`
quiz-chatbot-widget/
├── app/
│   ├── layout.tsx          # Root layout with dark mode
│   ├── page.tsx            # Main quiz widget with database integration
│   └── globals.css         # Global styles and design tokens
├── components/
│   ├── home-screen.tsx     # Quiz mode selection
│   ├── quiz-interface.tsx  # Question display and answering
│   ├── feedback-screen.tsx # Answer feedback with sources
│   ├── results-screen.tsx  # Final results summary
│   ├── theme-toggle.tsx    # Light/dark mode toggle
│   └── ui/                 # Reusable UI components
├── lib/
│   ├── api.ts              # Backend API service (database + mock data)
│   └── utils.ts            # Utility functions
└── .env.example            # Environment variables template
\`\`\`

## API Integration

The widget fetches questions from your SQLite database via the backend API:

- **Topics**: Fetched on home screen load from `/topics`
- **Questions**: Fetched from database via `/questions/random` (fast, parallel requests)
- **Daily Question**: Uses localStorage for 24-hour cooldown
- **Mock Mode**: Fallback to sample data when backend is unavailable

### Database vs Generation Mode

**Database Mode (Current - FAST)**:
- Calls `/questions/random` endpoint
- Fetches pre-stored questions from SQLite
- Instant response time
- No Ollama required

**Generation Mode (Optional - SLOW)**:
- Calls `/quiz` endpoint
- Generates new questions with Ollama
- Takes 10-30 seconds per question
- Requires Ollama running

## Customization

### Colors

Edit `app/globals.css` to customize the color scheme. The widget uses CSS custom properties for theming.

### Question Count

Modify question counts in `app/page.tsx`:
- Quick Quiz: Default 5 questions
- Daily Question: 1 question
- Scenario Task: Default 3 questions

### API Endpoint

Update `NEXT_PUBLIC_API_URL` in Project Settings to point to your backend.

## Deployment

### Frontend (Vercel)

1. Click "Publish" button in top right of v0
2. Or push your code to GitHub and import in Vercel
3. Add environment variables in Project Settings:
   - `NEXT_PUBLIC_API_URL` (your backend URL)
   - `NEXT_PUBLIC_USE_MOCK_DATA=false` (for production)
4. Deploy

### Backend

Deploy your FastAPI backend to your preferred platform and update the `NEXT_PUBLIC_API_URL` accordingly. Don't forget to:
- Include your `questions.db` file
- Update CORS settings with your production frontend URL

## Technologies

- **Frontend**: Next.js 14, React 19, TypeScript
- **Styling**: Tailwind CSS v4, shadcn/ui
- **Data Fetching**: Native fetch with parallel requests
- **Icons**: Lucide React
- **Backend**: FastAPI, SQLite, ChromaDB, Ollama (optional)

## License

MIT
