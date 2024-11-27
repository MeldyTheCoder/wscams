import React, { useEffect, useMemo, useRef, useState } from 'react';
import { io } from 'socket.io-client';
import styled from 'styled-components';
import { Grid2, Box, Button, CircularProgress, Container, MenuItem, Paper, Select, Snackbar, Stack, OutlinedInput, Typography } from '@mui/material';

const socket = io("ws://localhost:8080", {
  transports: ['websocket', 'polling'],
  withCredentials: false,
  autoConnect: false,
});

const NO_CAMERA_DETECTED_TEMPLATE_URL = 'https://i.ytimg.com/vi/w6geNk3QnBQ/maxresdefault.jpg';

type CamData = {
  picture: string;
  name: string;
  id: string;
}

type CamsListData = {
  [x: string]: CamData;
}

const ImageContainer = styled.div`
  position: relative;
  text-align: center;
  color: #f5f5f5;

  &, img {
    border-radius: 25px;
  }

  img {
    filter: blur(20px);
  }
`;

const ImageElement = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
`;

const LoaderContainer = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
`;

function App() {
  const [connected, setConnected] = useState<boolean>(false);
  const [camData, setCamData] = useState<CamsListData>({});
  const [selectedCamName, setSelectedCamName] = useState<string | null>(null);
  const [messages, setMessages] = useState<string[]>([]);

  const messageRef = useRef<any>();

  useEffect(() => {
    socket.connect();

    socket.on('connect', () => {
      socket.on('picture', (data: CamsListData) => {
        setCamData(data);
      });

      socket.on('cam_connected', ({cam_id: _, cam_name: camName}) => {
        setMessages((prev) => ([...prev, `Подключена новая камера: "${camName}".`]))
      })

      socket.on('cam_disconnected', ({cam_id: _, cam_name: camName}) => {
        setMessages((prev) => ([...prev, `Отключена камера: "${camName}".`]))
      })
      
      setConnected(true);
    });
  }, []);

  const selectedCam = useMemo(
    () => Object.values(camData).find((cam) => cam.name === selectedCamName), 
    [camData, selectedCamName]
  )

  const handleSendMessage = () => {
    const message = messageRef.current?.value;
    messageRef.current.value = ''

    if (!connected || !selectedCamName) {
      setMessages((prev) => [...prev, 'Сначала подключитесь к сети и выберите комп.']);
      return
    }

    socket.emit('send_message', {message: message, sid: selectedCam?.id});
  }

  const camImage = useMemo(() => {
    if (!selectedCam) {
      return (
        <Paper elevation={4}>
          <ImageContainer>
            <img
              src={process.env.PUBLIC_URL + '/stroev_pickme.jpg'}
              width={"100%"}
              height={"100%"}
              style={{
                backdropFilter: 'blur(6px)',
                zIndex: 0,
              }}
            />
            <ImageElement>
              <Typography variant='h5' sx={{xs: {display: 'none'}}}>
                Выберите устройство для отслеживания
              </Typography>
              <span style={{fontSize: '50px'}}>🥒</span>
            </ImageElement>
          </ImageContainer>
        </Paper>
      )
    }
  
    return (
      <Paper elevation={4} sx={{width: '100%', height: '100%'}}>
        <img
          src={!!selectedCam?.picture ? `data:image/png;base64, ${selectedCam.picture}` : NO_CAMERA_DETECTED_TEMPLATE_URL}
          width={"100%"}
          height={"100%"}
        />
      </Paper>
    )
  }, [selectedCamName, camData])

  const handleCamDataSelect = (camDataName: CamData['name']) => {
    setSelectedCamName(camDataName);
  };

  const handleClearMessage = (message: string) => {
    setMessages((prev) => prev.filter((m) => m !== message));
  }

  return (
    <Container sx={{position: 'relative', height: '100%'}}>
      <Box sx={{margin: '1rem'}}>
        {!connected ? (
          <LoaderContainer>
            <CircularProgress color="secondary" />
          </LoaderContainer>
        ) : (
          <Stack spacing={2} justifyContent="center" alignItems="center">
            {camImage}
            <Grid2 container columnSpacing={15} rowSpacing={3}>
              <Grid2>
                <Select
                  sx={{
                    minWidth: '300px',
                  }}
                  disabled={!connected || !camData}
                  value={selectedCam?.name || ''}
                  onChange={({target}) => {
                    handleCamDataSelect(`${target?.value}`);
                  }}
                >
                  {Object.values(camData).map((camData: CamData, index: number) => (
                    <MenuItem key={index} value={camData.name}>{camData.name}</MenuItem>
                  ))}
                  
                </Select>
              </Grid2>
              <Grid2>
                <OutlinedInput
                  inputRef={messageRef}
                  disabled={!selectedCamName}
                  placeholder="Сообщение"
                  endAdornment={<Button disabled={!selectedCamName} onClick={() => handleSendMessage()}>Отправить</Button>} 
                />
              </Grid2>
            </Grid2>
          </Stack>
        )}
        
        {messages.map((message) => (
          <Snackbar
            open
            message={message}
            autoHideDuration={3000}
            onClose={(_) => handleClearMessage(message)}
          />
        ))}
      </Box>
    </Container>
  );
}

export default App;
