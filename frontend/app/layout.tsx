import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AdLumen: The AI Ad Killer',
  description: 'Join the AdLumenati', // Illumenadti
  generator: 'v0.dev + Thomson Lam on 2 hours of sleep',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
