import React, { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { useTelegram } from './hooks/useTelegram';

const RegistrationPage = lazy(() =>
  import('./pages/RegistrationPage').then((module) => ({ default: module.RegistrationPage }))
);
const ResultsPage = lazy(() =>
  import('./pages/ResultsPage').then((module) => ({ default: module.ResultsPage }))
);
const AdminPage = lazy(() =>
  import('./pages/AdminPage').then((module) => ({ default: module.AdminPage }))
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});

const NavigationManager: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const { startParam } = useTelegram();

  useEffect(() => {
    if (startParam) {
      if (startParam.startsWith('contest_')) {
        const id = startParam.split('_')[1];
        navigate(`/register?contest_id=${id}`, { replace: true });
      } else if (startParam.startsWith('results_')) {
        const id = startParam.split('_')[1];
        navigate(`/results/${id}`, { replace: true });
      } else if (startParam === 'admin') {
        navigate('/admin', { replace: true });
      }
    }
  }, [startParam, navigate]);

  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <NavigationManager>
          <Layout>
            <Suspense fallback={<div className="px-6 py-10 text-center text-sm text-white/40">Загрузка...</div>}>
              <Routes>
                <Route path="/register" element={<RegistrationPage />} />
                <Route path="/results/:contestId" element={<ResultsPage />} />
                <Route path="/admin" element={<AdminPage />} />
                <Route path="*" element={<Navigate to="/register" replace />} />
              </Routes>
            </Suspense>
          </Layout>
        </NavigationManager>
      </Router>
    </QueryClientProvider>
  );
};

export default App;
