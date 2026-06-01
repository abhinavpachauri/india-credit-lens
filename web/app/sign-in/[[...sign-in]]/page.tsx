import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex items-center justify-center min-h-[70vh] px-4">
      <SignIn />
    </div>
  );
}
