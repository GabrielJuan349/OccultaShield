import { Routes } from '@angular/router';
import { LandingPage } from './pages/LandingPage/LandingPage';
import { LoginRegister } from './pages/LoginRegister/LoginRegister';
import { UploadPage } from './pages/UploadPage/UploadPage';
import { ReviewPage } from './pages/ReviewPage/ReviewPage';
import { DownloadPage } from './pages/DownloadPage/DownloadPage';
import { ProcessingPage } from './pages/ProcessingPage/ProcessingPage';
import { authGuard, roleGuard } from './guards/auth.guard';
import { AdminLayoutComponent } from './pages/Admin/AdminLayout/AdminLayout';
import { DashboardComponent } from './pages/Admin/Dashboard/Dashboard';
import { UsersComponent } from './pages/Admin/Users/Users';

export const routes: Routes = [
  {
    path: '',
    component: LandingPage
  },
  {
    path: 'admin',
    component: AdminLayoutComponent,
    // canActivate: [roleGuard],
    data: { role: 'admin' },
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', component: DashboardComponent },
      { path: 'users', component: UsersComponent }
    ]
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
    // canActivate: [authGuard]
  },
  {
    path: 'processing',
    component: ProcessingPage,
    // canActivate: [authGuard]
  },
  {
    path: '**',
    redirectTo: ''
  }
];
