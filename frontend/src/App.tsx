import { lazy } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./auth/AuthContext";
import { AppLayout, PublicLayout } from "./components/Layout";
import Landing from "./pages/Landing";
import NotFound from "./pages/NotFound";

// Découpage par route : le formulaire (zod, react-hook-form) et l'app ne pèsent pas sur la landing.
const Login = lazy(() => import("./pages/Auth").then((m) => ({ default: m.Login })));
const Register = lazy(() => import("./pages/Auth").then((m) => ({ default: m.Register })));
const Feed = lazy(() => import("./pages/Feed"));
const Impact = lazy(() => import("./pages/Impact"));
const ListingDetail = lazy(() => import("./pages/ListingDetail"));
const CreateListing = lazy(() => import("./pages/CreateListing"));
const MyListings = lazy(() => import("./pages/MyListings"));
const MyClaims = lazy(() => import("./pages/Claims").then((m) => ({ default: m.MyClaims })));
const ProviderPickups = lazy(() => import("./pages/Claims").then((m) => ({ default: m.ProviderPickups })));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route element={<PublicLayout />}>
              <Route index element={<Landing />} />
              <Route path="login" element={<Login />} />
              <Route path="register" element={<Register />} />
              <Route path="*" element={<NotFound />} />
            </Route>
            <Route path="app" element={<AppLayout />}>
              <Route index element={<Feed />} />
              <Route path="listings/:id" element={<ListingDetail />} />
              <Route path="new" element={<CreateListing />} />
              <Route path="mine" element={<MyListings />} />
              <Route path="claims" element={<MyClaims />} />
              <Route path="pickups" element={<ProviderPickups />} />
              <Route path="impact" element={<Impact />} />
            </Route>
          </Routes>
          <Toaster position="bottom-center" toastOptions={{ className: "font-sans" }} />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
