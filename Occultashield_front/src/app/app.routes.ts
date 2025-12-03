import { Routes } from '@angular/router';
import { LandingPage } from './pages/LandingPage/LandingPage';
import { LoginRegister } from './pages/LoginRegister/LoginRegister';
import { UploadPage } from './pages/UploadPage/UploadPage';
import { ReviewPage } from './pages/ReviewPage/ReviewPage';
import { DownloadPage } from './pages/DownloadPage/DownloadPage';
import { ProcessingPage } from './pages/ProcessingPage/ProcessingPage';

export const routes: Routes = [
  {
    path: '',
    component: LandingPage
  },
  {
    path: 'login',
    component: LoginRegister,
  },
  {
    path: 'upload',
    component: UploadPage,
    // canActivate: [authGuard]
  },
  {
    path: 'download',
    component: DownloadPage,
    // canActivate: [authGuard]
  },
  {
    path: 'review',
    component: ReviewPage,
  },
  {
    path: 'processing',
    component: ProcessingPage,
  },
  {
    path: '**',
    redirectTo: ''
  }
];
