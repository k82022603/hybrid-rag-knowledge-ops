import { Box, Typography, Button, Card, CardContent, Grid } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DescriptionIcon from '@mui/icons-material/Description';

/**
 * KnowledgePage - 지식 관리 페이지
 *
 * 문서 업로드, 관리, 처리 상태 모니터링
 */
const KnowledgePage: React.FC = () => {
  // TODO: 실제 문서 관리 기능 구현

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 4,
        }}
      >
        <Box>
          <Typography variant="h4" gutterBottom>
            Knowledge Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Upload and manage documents
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<CloudUploadIcon />}
          size="large"
        >
          Upload Document
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Documents
              </Typography>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: 200,
                  color: 'text.secondary',
                }}
              >
                <Box sx={{ textAlign: 'center' }}>
                  <DescriptionIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
                  <Typography>No documents uploaded yet</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Processing Status
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Document processing queue status will be displayed here...
              </Typography>
            </CardContent>
          </Card>

          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Knowledge Graph
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Graph visualization will be displayed here...
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default KnowledgePage;
