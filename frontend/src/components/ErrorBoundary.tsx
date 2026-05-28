/**
 * ErrorBoundary — Production-grade crash guard
 * 
 * Catches React render errors and displays a recovery UI instead of 
 * a white screen of death. Required for App Store compliance.
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button, Typography, Card, Empty } from '@douyinfe/semi-ui';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

const { Title, Text, Paragraph } = Typography;

interface Props {
  children: ReactNode;
  /** Optional custom fallback UI */
  fallback?: ReactNode;
  /** Section name for error reporting */
  section?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    
    // Log to console in development, could send to error tracking service
    console.error(
      `[ErrorBoundary${this.props.section ? ` - ${this.props.section}` : ''}]`,
      error,
      errorInfo
    );
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleReload = (): void => {
    window.location.reload();
  };

  handleGoHome = (): void => {
    window.location.href = '/dashboard';
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '50vh',
            padding: '40px 20px',
          }}
        >
          <Card
            style={{
              maxWidth: 480,
              width: '100%',
              textAlign: 'center',
              borderRadius: 16,
              boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
            }}
            bodyStyle={{ padding: '40px 32px' }}
          >
            <Empty
              image={
                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #fee2e2, #fecaca)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 16px',
                  }}
                >
                  <AlertTriangle size={32} color="#ef4444" />
                </div>
              }
              title=""
              description=""
            />

            <Title heading={4} style={{ marginBottom: 8 }}>
              Đã xảy ra lỗi
            </Title>

            <Paragraph type="tertiary" style={{ marginBottom: 24 }}>
              {this.props.section
                ? `Phần "${this.props.section}" gặp sự cố. Các phần khác vẫn hoạt động bình thường.`
                : 'Ứng dụng gặp sự cố không mong muốn. Vui lòng thử lại.'}
            </Paragraph>

            {import.meta.env.DEV && this.state.error && (
              <div
                style={{
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: 8,
                  padding: '12px 16px',
                  marginBottom: 24,
                  textAlign: 'left',
                  maxHeight: 120,
                  overflow: 'auto',
                }}
              >
                <Text type="danger" size="small" style={{ fontFamily: 'monospace' }}>
                  {this.state.error.message}
                </Text>
              </div>
            )}

            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <Button
                icon={<RefreshCw size={16} />}
                theme="solid"
                type="primary"
                onClick={this.handleReset}
              >
                Thử lại
              </Button>
              <Button
                icon={<Home size={16} />}
                theme="outline"
                onClick={this.handleGoHome}
              >
                Về trang chủ
              </Button>
            </div>

            <div style={{ marginTop: 16 }}>
              <Text
                link
                type="tertiary"
                size="small"
                onClick={this.handleReload}
                style={{ cursor: 'pointer' }}
              >
                Tải lại trang
              </Text>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
