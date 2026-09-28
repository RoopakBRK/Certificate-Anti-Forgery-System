# CAFS (Certificate Anti Forgery System) Frontend

Modern certificate verification platform frontend built with Next.js 14, TypeScript, and Tailwind CSS.

## 🚀 Features

- **Modern Tech Stack**: Next.js 14 with App Router, TypeScript, and Tailwind CSS
- **Drag & Drop Upload**: Intuitive file upload interface with drag-and-drop support
- **Real-time Validation**: Client-side file type and size validation
- **Responsive Design**: Mobile-first design with beautiful gradients and modern UI
- **Type Safety**: Full TypeScript coverage with strict type checking
- **API Integration**: Clean service layer for backend communication

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── globals.css         # Global styles
│   │   ├── layout.tsx          # Root layout
│   │   └── page.tsx            # Landing page
│   ├── components/
│   │   ├── ui/                 # Reusable UI components
│   │   └── verification/       # Domain-specific components
│   │       └── UploadForm.tsx
│   ├── services/               # API integration layer
│   │   └── api.ts
│   └── types/                  # TypeScript type definitions
│       └── index.ts
├── .env.local                  # Environment variables
├── next.config.mjs             # Next.js configuration
├── tailwind.config.ts          # Tailwind CSS configuration
└── tsconfig.json               # TypeScript configuration
```

## 🛠️ Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
Create a `.env.local` file with:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## 📝 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## 🔌 API Integration

The frontend communicates with the FastAPI backend via the service layer in `src/services/api.ts`. 

Current endpoint:
- **POST** `/api/v1/verify` - Upload certificate for verification

## 🎨 Design System

- **Colors**: Tailwind's slate and blue palettes
- **Typography**: Inter font family
- **Components**: Custom UI components with consistent styling
- **Icons**: Lucide React icon library

## 🔒 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## 📦 Dependencies

### Core
- `next` - React framework
- `react` & `react-dom` - React library
- `typescript` - Type safety

### UI
- `tailwindcss` - Utility-first CSS framework
- `lucide-react` - Icon library

### Dev Tools
- `eslint` - Code linting
- `autoprefixer` - CSS vendor prefixes
- `postcss` - CSS processing

## 🏗️ Architecture

This frontend follows a **monorepo sibling architecture**, designed to be:
- **Decoupled**: Independent from backend implementation details
- **Scalable**: Clean separation of concerns
- **Type-safe**: Full TypeScript coverage
- **Maintainable**: Organized by feature and domain

## 📄 License

Part of the CAFS (Certificate Anti Forgery System) platform.
