import Header from './components/Header';
import Hero from './components/Hero';
import Services from './components/Services';
import Solutions from './components/Solutions';
import Partners from './components/Partners';
import CTA from './components/CTA';
import Footer from './components/Footer';

export default function App() {
  return (
    <div className="min-h-screen bg-bg">
      <Header />
      <Hero />
      <Services />
      <Solutions />
      <Partners />
      <CTA />
      <Footer />
    </div>
  );
}
