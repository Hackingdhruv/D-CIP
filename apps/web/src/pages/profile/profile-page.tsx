import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Camera, KeyRound, Monitor, Shield, Trash2, User } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { PasswordStrength } from '@/components/common/password-strength';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { useAuth, useChangePassword, useUpdateProfile } from '@/hooks/use-auth';
import { useSessions, useRevokeSession, useRevokeAllSessions, useUploadAvatar } from '@/hooks/use-sessions';
import { ApiRequestError } from '@/lib/api-client';
import { env } from '@/config/env';

const profileSchema = z.object({
  fullName: z.string().min(1, 'Full name is required.').max(255),
});

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required.'),
    newPassword: z
      .string()
      .min(8, 'At least 8 characters.')
      .regex(/[A-Z]/, 'Uppercase required.')
      .regex(/[a-z]/, 'Lowercase required.')
      .regex(/[0-9]/, 'Digit required.')
      .regex(/[^A-Za-z0-9]/, 'Special character required.'),
    confirmPassword: z.string().min(1, 'Confirm your password.'),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: "Passwords don't match.",
    path: ['confirmPassword'],
  });

type ProfileForm = z.infer<typeof profileSchema>;
type PasswordForm = z.infer<typeof passwordSchema>;

function formatRelativeTime(dateStr: string) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function parseDevice(userAgent: string | null) {
  if (!userAgent) return { device: 'Unknown device', browser: 'Unknown browser' };
  const ua = userAgent.toLowerCase();
  const browser = ua.includes('chrome') ? 'Chrome'
    : ua.includes('firefox') ? 'Firefox'
    : ua.includes('safari') ? 'Safari'
    : ua.includes('edge') ? 'Edge'
    : 'Browser';
  const device = ua.includes('mobile') ? 'Mobile'
    : ua.includes('tablet') ? 'Tablet'
    : 'Desktop';
  return { device, browser };
}

export function ProfilePage() {
  const { user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [newPasswordValue, setNewPasswordValue] = useState('');

  const { mutateAsync: updateProfile, isPending: savingProfile } = useUpdateProfile();
  const { mutateAsync: changePassword, isPending: changingPw } = useChangePassword();
  const { mutateAsync: uploadAvatar, isPending: uploadingAvatar } = useUploadAvatar();
  const { data: sessions, isLoading: loadingSessions } = useSessions();
  const { mutate: revokeSession, isPending: revoking } = useRevokeSession();
  const { mutate: revokeAll, isPending: revokingAll } = useRevokeAllSessions();

  const profileForm = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: { fullName: user?.fullName ?? '' },
  });

  const passwordForm = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { currentPassword: '', newPassword: '', confirmPassword: '' },
  });

  const onSaveProfile = async (values: ProfileForm) => {
    try {
      await updateProfile(values);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Update failed.');
    }
  };

  const onChangePassword = async (values: PasswordForm) => {
    try {
      await changePassword({
        currentPassword: values.currentPassword,
        newPassword: values.newPassword,
      });
      passwordForm.reset();
      setNewPasswordValue('');
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Password change failed.');
    }
  };

  const onAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await uploadAvatar(file);
    } catch {
      // error already shown via hook
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const initials = user?.fullName
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase() ?? '?';

  if (!user) return null;

  return (
    <div className="space-y-6">
      <PageHeader title="My Account" description="Manage your profile, security and active sessions." />

      <Tabs defaultValue="profile">
        <TabsList className="w-full max-w-sm">
          <TabsTrigger value="profile" className="flex-1">
            <User className="mr-1.5 h-4 w-4" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="security" className="flex-1">
            <KeyRound className="mr-1.5 h-4 w-4" />
            Security
          </TabsTrigger>
          <TabsTrigger value="sessions" className="flex-1">
            <Monitor className="mr-1.5 h-4 w-4" />
            Sessions
          </TabsTrigger>
          <TabsTrigger value="access" className="flex-1">
            <Shield className="mr-1.5 h-4 w-4" />
            Access
          </TabsTrigger>
        </TabsList>

        {/* ── Profile Tab ── */}
        <TabsContent value="profile" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Profile information</CardTitle>
              <CardDescription>Update your display name and profile photo.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar */}
              <div className="flex items-center gap-5">
                <div className="relative">
                  <Avatar className="h-20 w-20 border-2 border-border">
                    {user.avatarUrl && (
                      <AvatarImage src={`${new URL(env.apiBaseUrl).origin}${user.avatarUrl}`} alt={user.fullName} />
                    )}
                    <AvatarFallback className="bg-primary/10 text-2xl font-semibold text-primary">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingAvatar}
                    className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full border border-border bg-card shadow-sm hover:bg-accent transition-colors disabled:opacity-50"
                    aria-label="Upload avatar"
                  >
                    {uploadingAvatar ? (
                      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    ) : (
                      <Camera className="h-3.5 w-3.5" />
                    )}
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    className="hidden"
                    onChange={onAvatarChange}
                  />
                </div>
                <div>
                  <p className="font-semibold">{user.fullName}</p>
                  <p className="text-sm text-muted-foreground">{user.email}</p>
                  <p className="text-xs text-muted-foreground">@{user.username}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    JPEG, PNG, WebP or GIF · max 5 MB
                  </p>
                </div>
              </div>

              <Separator />

              <Form {...profileForm}>
                <form onSubmit={profileForm.handleSubmit(onSaveProfile)} className="max-w-sm space-y-4">
                  <FormField
                    control={profileForm.control}
                    name="fullName"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Full name</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={savingProfile}>
                    {savingProfile ? 'Saving…' : 'Save changes'}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Security Tab ── */}
        <TabsContent value="security" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Change password</CardTitle>
              <CardDescription>
                Use a strong password with uppercase, lowercase, digits and special characters.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...passwordForm}>
                <form
                  onSubmit={passwordForm.handleSubmit(onChangePassword)}
                  className="max-w-sm space-y-4"
                >
                  <FormField
                    control={passwordForm.control}
                    name="currentPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Current password</FormLabel>
                        <FormControl>
                          <Input type="password" autoComplete="current-password" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={passwordForm.control}
                    name="newPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>New password</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            autoComplete="new-password"
                            {...field}
                            onChange={(e) => {
                              field.onChange(e);
                              setNewPasswordValue(e.target.value);
                            }}
                          />
                        </FormControl>
                        <PasswordStrength password={newPasswordValue} />
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={passwordForm.control}
                    name="confirmPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Confirm new password</FormLabel>
                        <FormControl>
                          <Input type="password" autoComplete="new-password" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={changingPw}>
                    {changingPw ? 'Updating…' : 'Update password'}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Sessions Tab ── */}
        <TabsContent value="sessions" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Active sessions</CardTitle>
                  <CardDescription>
                    Devices currently signed in to your account. Revoke any you don't recognise.
                  </CardDescription>
                </div>
                {sessions && sessions.length > 1 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => revokeAll()}
                    disabled={revokingAll}
                  >
                    {revokingAll ? 'Revoking…' : 'Revoke all others'}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {loadingSessions ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-16 w-full rounded-lg" />
                  ))}
                </div>
              ) : sessions && sessions.length > 0 ? (
                <div className="space-y-2">
                  {sessions.map((session) => {
                    const { device, browser } = parseDevice(session.userAgent);
                    return (
                      <div
                        key={session.id}
                        className="flex items-center justify-between rounded-lg border border-border p-3.5 transition-colors hover:bg-muted/30"
                      >
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
                            <Monitor className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div className="space-y-0.5">
                            <p className="text-sm font-medium">
                              {browser} on {device}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {session.ipAddress ?? 'Unknown IP'} · Last active {formatRelativeTime(session.lastActiveAt)}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Started {new Date(session.createdAt).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => revokeSession(session.id)}
                          disabled={revoking}
                        >
                          <Trash2 className="h-4 w-4" />
                          Revoke
                        </Button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="py-8 text-center">
                  <Monitor className="mx-auto h-8 w-8 text-muted-foreground/50" />
                  <p className="mt-2 text-sm text-muted-foreground">No active sessions found.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Access Tab ── */}
        <TabsContent value="access" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Roles &amp; permissions</CardTitle>
              <CardDescription>Your current access level on this platform.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Assigned roles
                </p>
                <div className="flex flex-wrap gap-2">
                  {user.roles.length > 0 ? (
                    user.roles.map((role) => (
                      <Badge key={role.id} variant="secondary" className="px-3 py-1">
                        {role.name}
                      </Badge>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No roles assigned.</p>
                  )}
                </div>
              </div>
              <Separator />
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Permissions
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {user.permissions.length > 0 ? (
                    user.permissions.map((p) => (
                      <Badge key={p} variant="outline" className="font-mono text-xs">
                        {p}
                      </Badge>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No permissions.</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
