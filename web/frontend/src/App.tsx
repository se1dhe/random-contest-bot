import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { RegistrationPage } from './pages/RegistrationPage';
import { ResultsPage } from './pages/ResultsPage';
import { AdminPage } from './pages/AdminPage';
import { useTelegram } from './hooks/useTelegram';

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
            <Routes>
              <Route path="/register" element={<RegistrationPage />} />
              <Route path="/results/:contestId" element={<ResultsPage />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="*" element={<Navigate to="/register" replace />} />
            </Routes>
          </Layout>
        </NavigationManager>
      </Router>
    </QueryClientProvider>
  );
};

export default App;
