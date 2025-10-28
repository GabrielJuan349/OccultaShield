import { Routes } from '@angular/router';
import { LoginRegister } from './pages/LoginRegister/LoginRegister';
import { LandingPage } from './pages/LandingPage/LandingPage';
import { UploadPage } from './pages/UploadPage/UploadPage';
import { DownloadPage } from './pages/DownloadPage/DownloadPage';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    component: LandingPage,
  },
  {
    path: 'login',
    component: LoginRegister,
  },
  {
    path: 'upload',
    component: UploadPage,
    canActivate: [authGuard]
  },
  {
    path: 'download',
    component: DownloadPage,
    canActivate: [authGuard]
  },
  {
    path: 'quiz',
    component: LandingPage,
  },
  {
    path: '**',
    redirectTo: ''
  }
];
