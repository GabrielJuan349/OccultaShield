import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  {
    path: '**',
    renderMode: RenderMode.Server
  },
  {
    path: 'login',
    renderMode: RenderMode.Client
  },
    {
    path: 'upload',
    renderMode: RenderMode.Prerender
  },
  {
    path: 'download',
    renderMode: RenderMode.Prerender
  },
  {
    path:'review',
    renderMode: RenderMode.Prerender
  },
  {
    path: 'processing',
    renderMode: RenderMode.Prerender
  }
];
