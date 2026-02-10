import FacebookPixel from '@/components/ui/FacebookPixel';
import GoogleAnalytics from '@/components/ui/GoogleAnalytics';
import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

// ============================================================================
// SEO METADATA - TUCUNARÉ BOT
// ============================================================================
export const metadata: Metadata = {
  metadataBase: new URL('https://tucunarebot.com.br'),
  title: {
    default:
      'TucunaréBot - Robô de Automação para Crash Game | Bot Inteligente',
    template: '%s | TucunaréBot',
  },
  description:
    'O TucunaréBot é um sistema de automação com interceptação WebSocket e IA para Crash Game. Precisão total, latência zero e disciplina algorítmica. Opere 24/7 com inteligência artificial.',
  keywords: [
    'bot crash',
    'crash game bot',
    'robô crash',
    'automação crash',
    'bot blaze',
    'crash blaze',
    'robô apostas',
    'bot aviator',
    'crash aviator',
    'software crash',
    'automação apostas',
    'bot inteligente',
    'crash game automatico',
    'robo para crash',
    'bot para blaze',
    'tucunare bot',
    'tucunaré bot',
  ],
  authors: [{ name: 'TucunaréBot', url: 'https://tucunarebot.com.br' }],
  creator: 'TucunaréBot',
  publisher: 'Tucunaré Locação de Máquinas e Equipamentos LTDA',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'pt_BR',
    url: 'https://tucunarebot.com.br',
    title: 'TucunaréBot - Robô de Automação para Crash Game',
    description:
      'Sistema de automação com WebSocket e IA. Precisão total, latência zero, opere 24/7.',
    siteName: 'TucunaréBot',
    images: [
      {
        url: 'https://tucunarebot.com.br/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'TucunaréBot - Robô de Automação para Crash Game',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'TucunaréBot - Robô de Automação para Crash Game',
    description:
      'Sistema de automação com WebSocket e IA. Precisão total, latência zero.',
    images: ['https://tucunarebot.com.br/og-image.jpg'],
  },
  alternates: {
    canonical: 'https://tucunarebot.com.br',
  },
  category: 'technology',
};

// Schema.org JSON-LD para rich snippets no Google
const organizationSchema = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'TucunaréBot',
  legalName: 'Tucunaré Locação de Máquinas e Equipamentos LTDA',
  url: 'https://tucunarebot.com.br',
  logo: 'https://tucunarebot.com.br/logo.png',
  description: 'Sistema de automação com WebSocket e IA para Crash Game.',
  address: {
    '@type': 'PostalAddress',
    addressLocality: 'Tangará da Serra',
    addressRegion: 'MT',
    addressCountry: 'BR',
  },
  contactPoint: {
    '@type': 'ContactPoint',
    telephone: '+55-65-99272-7497',
    contactType: 'sales',
    availableLanguage: ['Portuguese'],
  },
};

const softwareSchema = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'TucunaréBot',
  applicationCategory: 'GameApplication',
  operatingSystem: 'Windows, macOS',
  offers: {
    '@type': 'Offer',
    price: '69.00',
    priceCurrency: 'BRL',
    availability: 'https://schema.org/InStock',
  },
  aggregateRating: {
    '@type': 'AggregateRating',
    ratingValue: '4.8',
    ratingCount: '150',
  },
  description:
    'Robô de automação para Crash Game com interceptação WebSocket e inteligência artificial.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <head>
        {/* Schema.org JSON-LD para rich snippets */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(organizationSchema),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(softwareSchema),
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {/* Google Analytics */}
        <GoogleAnalytics />
        {/* Facebook Pixel */}
        <FacebookPixel /> {/* <--- ADICIONADO AQUI */}
        {children}
      </body>
    </html>
  );
}
